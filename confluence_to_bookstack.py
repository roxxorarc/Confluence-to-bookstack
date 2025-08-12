from functools import lru_cache
import os
from typing import Dict, Optional
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from utils import logger, DepthLevel
from content_processor import ContentProcessor
from bookstack_client import BookStackClient
import warnings

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


class ConfluenceToBookstack:
    def __init__(self, config):
        self.config = config
        self.api_client = BookStackClient(config)
        self.content_processor = ContentProcessor(config, self.api_client)
        
        self.created_objects = {
            "shelves": {},
            "books": {},
            "chapters": {},
            "pages": {},
        }
        self.deleted_objects = {
            "shelf": 0,
            "book": 0,
        }
        
        self.errors = 0

    @lru_cache(maxsize=128)
    def _read_file_cached(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            self.errors += 1
            return None

    def _add_shelf(self, item: Dict, shelf_id):
        self.created_objects["shelves"][shelf_id] = {
            "title": item["title"],
            "id": shelf_id,
        }

    def _add_book(self, item: Dict, shelf_id, book_id):
        self.created_objects["books"][book_id] = {
            "title": item["title"],
            "id": book_id,
            "shelf_id": shelf_id,
        }

    def _add_chapter(self, item: Dict, chapter_id):
        self.created_objects["chapters"][chapter_id] = {
            "title": item["title"],
            "id": chapter_id,
        }

    def _add_page(self, item: Dict, page_id):
        self.created_objects["pages"][page_id] = {
            "title": item["title"],
            "id": page_id,
        }

    def run(self):
        self.api_client.test_endpoints()
        self.find_index_files()
        self.link_books_to_shelves()
        self.print_report()
        

    def link_books_to_shelves(self):
        for shelf in self.created_objects["shelves"].values():
            shelf_id = shelf["id"]

            associated_books = []
            for book in self.created_objects["books"].values():
                if book.get("shelf_id") == shelf_id:
                    associated_books.append(book["id"])

            if associated_books:
                success, shelf_info = self.api_client.request("GET", f"/shelves/{shelf_id}")
                if success:
                    update_payload = {
                        "name": shelf_info.get("name"),
                        "description_html": shelf_info.get("description_html", ""),
                        "books": associated_books,
                        "tags": shelf_info.get("tags", []),
                    }

                    success, response = self.api_client.request(
                        "PUT", f"/shelves/{shelf_id}", update_payload
                    )
                    if success:
                        logger.info(
                            f"Shelf '{shelf['title']}' updated with {len(associated_books)} book(s)"
                        )
                    else:
                        logger.error(
                            f"Failed to update shelf '{shelf['title']}': {response}"
                        )
                        self.errors += 1

    def clear(self):
        self.deleted_objects = self.api_client.clear_content()
        self.print_report(clear=True)

    def parse_index_html(self, index_path: str) -> Dict:
        try:
            with open(index_path, "r", encoding="utf-8") as file:
                content = file.read()
            soup = BeautifulSoup(content, "html.parser")
            pages_section = soup.find_all("div", class_="pageSection")
            pages_section = pages_section[1] if pages_section else None
            if not pages_section:
                logger.warning(f"pageSection div not found in {index_path}")
                return {}

            hierarchy_ul = pages_section.find("ul")
            if not hierarchy_ul:
                logger.warning(f"Hierarchy UL not found in {index_path}")
                return {}

            hierarchy = self.parse_ul_hierarchy(hierarchy_ul, level=1)

            return {"source_file": index_path, "hierarchy": hierarchy}

        except Exception as e:
            logger.error(f"Error parsing {index_path}: {e}")
            self.errors += 1
            return {}

    def parse_ul_hierarchy(self, ul_element: BeautifulSoup, level: int) -> Dict:
        subpages = []
        for li in ul_element.find_all("li", recursive=False):
            link = li.find("a")
            if not link:
                continue

            href = link.get("href", "")
            title = link.get_text().strip()

            page = {
                "title": title,
                "href": href,
                "level": level,
                "type": DepthLevel.from_level(level),
                "children": [],
            }

            sub_uls = li.find_all("ul", recursive=False)
            for sub_ul in sub_uls:
                children = self.parse_ul_hierarchy(sub_ul, level + 1)
                page["children"].extend(children)

            subpages.append(page)

        return subpages

    def find_index_files(self):
        index_file = []
        for root, _, files in os.walk(self.config.SOURCE_PATH):
            if "index.html" in files:
                index_file = os.path.join(root, "index.html")

        logger.info(f"Found index.html at {index_file}")
        parsed_data = self.parse_index_html(index_file)
        if parsed_data and "hierarchy" in parsed_data:
            self.process_data(parsed_data)
        else:
            logger.warning("No hierarchy found in the index.html file.")

    def process_data(self, data: Dict):
        for item in data.get("hierarchy", []):
            self.process_item(item)

    def print_report(self, clear: bool = False):
        """Prints a summary report of the migration process"""
        if clear:
            logger.info(f"Shelves cleared: {self.deleted_objects['shelf']}")
            logger.info(f"Books cleared: {self.deleted_objects['book']}")
        else:        
            logger.info(f"Shelves created: {len(self.created_objects['shelves'])}")
            logger.info(f"Books created: {len(self.created_objects['books'])}")
            logger.info(f"Chapters created: {len(self.created_objects['chapters'])}")
            logger.info(f"Pages created: {len(self.created_objects['pages'])}")

        logger.info(f"Errors encountered while processing: {len(self.content_processor.errors)}")
        logger.info(f"Total errors encountered: {self.errors + len(self.content_processor.errors)}")

    def process_item(self, item: Dict, shelf_id: Optional[str] = None, 
                     book_id: Optional[str] = None, chapter_id: Optional[str] = None):
        match item["type"]:
            case DepthLevel.SHELF:
                shelf_id = self.add_item(DepthLevel.SHELF, "/shelves", item)
                self._add_shelf(item, shelf_id)

            case DepthLevel.BOOK:
                book_id = self.add_item(DepthLevel.BOOK, "/books", item)
                page_id = self.add_item(DepthLevel.PAGE, "/pages", item, {"book_id": book_id})
                self._add_book(item, shelf_id, book_id)
                self._add_page(item, page_id)

            case DepthLevel.CHAPTER:
                if item.get("children") == []:
                    # relevant to create chapter then page ?
                    page_id = self.add_item(DepthLevel.PAGE, "/pages", item, {"book_id": book_id})
                else:
                    chapter_id = self.add_item(DepthLevel.CHAPTER, "/chapters", item, {"book_id": book_id})
                    page_id = self.add_item(DepthLevel.PAGE, "/pages", item, {"book_id": book_id, "chapter_id": chapter_id})
                    self._add_chapter(item, chapter_id)
                self._add_page(item, page_id)
                    
            case DepthLevel.PAGE:
                page_id = self.add_item(DepthLevel.PAGE, "/pages", item, {"book_id": book_id, "chapter_id": chapter_id})
                self._add_page(item, page_id)

            case _:
                logger.warning(f"Unknown type for item: {item['title']}")
                
        for child in item.get("children", []):
            self.process_item(child, shelf_id, book_id, chapter_id)

    def add_item(self, type: DepthLevel, endpoint: str, item: Dict, additional_data: Dict = None):
        """Creates an item in BookStack and returns its ID"""
        payload, title = self.generate_payload(item, type, additional_data)
        success, response = self.api_client.request("POST", endpoint, payload)
        if success:
            item_id = response.get("id")
            # logger.info(f"{str(type)} created: '{title}' (ID: {item_id})")
        else:
            logger.error(f"Failed to create {str(type)} '{title}': {response}")
            self.errors += 1
            return None
        if type == DepthLevel.PAGE:
            try:
                updated_payload, title = self.generate_payload(item, type, additional_data, str(item_id))
                success, response = self.api_client.request("PUT", f"/pages/{item_id}", updated_payload)
                if success:
                    logger.info(f"Page '{title}' updated with processed attachments")
                else:
                    logger.warning(f"Page '{title}' created but failed to update with attachments")
            except Exception as e:
                logger.error(f"Error updating page with attachments: {e}")
                self.errors += 1
            return item_id
        return item_id

    def generate_payload(self, item: Dict, item_type: DepthLevel, additional_data: Dict = None, page_id: Optional[str] = None) -> Dict:
        title, description = self.content_processor.extract_content_from_file(item["href"], item_type, page_id)
        base_payload = {
            "name": title,
            "tags": [
                {"name": "Source", "value": "Confluence"},
                {"name": "Type", "value": str(item_type)},
            ]
        }

        match item_type:
            case DepthLevel.SHELF:
                base_payload.update({"description_html": "", "books": []})
            case DepthLevel.CHAPTER:
                base_payload["description_html"] = ""
            case DepthLevel.PAGE:
                base_payload["html"] = description
        if additional_data:
            base_payload.update(additional_data)

        return base_payload, title
        
            
