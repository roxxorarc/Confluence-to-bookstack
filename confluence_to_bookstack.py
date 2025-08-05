from functools import lru_cache
import json
from operator import concat
import os
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import requests
from utils import logger, DepthLevel


class ConfluenceToBookstack:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Authorization": f'Token {getattr(config, "BOOKSTACK_API_ID", "")}:{getattr(config, "BOOKSTACK_API_SECRET", "")}'
        }

    @lru_cache(maxsize=128)
    def _read_file_cached(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def run(self):
        self.test_bookstack_endpoints()
        self.find_index_files()

    def test_bookstack_endpoints(self):
        try:
            if not self.config.BOOKSTACK_URL:
                logger.error("BookStack URL is missing")
                return

            response = requests.get(
                f"{self.config.BOOKSTACK_URL}", headers=self.headers
            )
            logger.info(f"Testing BookStack API at {self.config.BOOKSTACK_URL}")

            if response.status_code == 200:
                logger.info(f"API returned {response.status_code}")
            else:
                logger.warning(
                    f"API returned unexpected status code: {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Unexpected error while testing endpoints: {e}")

    def api_request(
        self, method: str, endpoint: str, data: Dict = None
    ) -> Tuple[bool, Dict]:

        url = f"{self.config.BOOKSTACK_URL}{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text,
                }

        except Exception as e:
            return False, {"error": str(e)}

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

        self.print_report()

    def process_data(self, data: Dict):
        for item in data.get("hierarchy", []):
            self.process_item(item)

    def print_report(self):
        pass

    def process_item(self, item: Dict, shelf_id: Optional[str] = None, 
                     book_id: Optional[str] = None, chapter_id: Optional[str] = None):
        match item["type"]:
            case DepthLevel.SHELF:
                shelf_id = self.add_item(DepthLevel.SHELF, "/shelves", item)
                
            case DepthLevel.BOOK:
                if item.get("children") == []:
                    book_id = self.add_item(DepthLevel.BOOK, "/books", item)
                    self.add_item(DepthLevel.PAGE, "/pages", item, {"book_id": book_id})
                else:
                    book_id = self.add_item(DepthLevel.BOOK, "/books", item)
                    
            case DepthLevel.CHAPTER:
                if item.get("children") == []:
                    self.add_item(DepthLevel.PAGE, "/pages", item, {"book_id": book_id})
                else:
                    chapter_id = self.add_item(DepthLevel.CHAPTER, "/chapters", item, {"book_id": book_id})
                    
            case DepthLevel.PAGE:
                self.add_item(DepthLevel.PAGE, "/pages", item, {"book_id": book_id, "chapter_id": chapter_id})
                
            case _:
                logger.warning(f"Unknown type for item: {item['title']}")
                
        for child in item.get("children", []):
            self.process_item(child, shelf_id, book_id, chapter_id)

    def add_item(self, type: DepthLevel, endpoint: str, item: Dict, additional_data: Dict = None):
        payload, title = self.generate_payload(item, type, additional_data)
        success, response = self.api_request("POST", endpoint, payload)
        if success:
            item_id = response.get("id")
            logger.info(f"{str(type)} created: '{title}' (ID: {item_id})")
            return item_id
        else:
            print(additional_data)
            logger.error(f"Failed to create {str(type)} '{title}': {response}")
            return None

    def extract_content_from_file(self, file_path: str, item_type: DepthLevel) -> Tuple[str, str]:
        full_path = self.config.SOURCE_PATH + "/" + file_path
        content = self._read_file_cached(str(full_path))
        
        
        if not content:
            return "Error", f"<p>Error generating content</p>"

        soup = BeautifulSoup(content, "html.parser")
        title = soup.title.get_text(strip=True)
        
        if item_type == DepthLevel.SHELF:
            inner_cell = soup.select_one("div.innerCell")
            description = self._reconstruct_dom_content(inner_cell)
        else:
            main_content = soup.select_one("div#main-content")

            if main_content:
                description = self._reconstruct_dom_content(main_content)
            else:
                paragraphs = soup.select("p")[:3]
                description = "".join(
                    self._reconstruct_dom_content(p) for p in paragraphs)       
                
        print(f"Extracted title: {title}")
        print(description)     
        return title, description or f"<p>Content migrated from {file_path}</p>"

    def reconstruct_dom_content(self, element: Tag) -> str:
        if not element:
            return ""

        try:
            if element.name is None:
                return element.string.strip() if element.string else ""

            IMPORTANT_ATTRS = frozenset(
                [
                    "id",
                    "class",
                    "style",
                    "href",
                    "src",
                    "alt",
                    "title",
                    "colspan",
                    "rowspan",
                    "width",
                    "height",
                ]
            )

            new_soup = BeautifulSoup("", "html.parser")
            new_elem = new_soup.new_tag(element.name)

            for attr in IMPORTANT_ATTRS:
                if element.has_attr(attr):
                    new_elem[attr] = element[attr]

            for child in element.contents:
                if hasattr(child, "name"):
                    rebuilt_child = self._reconstruct_dom_content(child)
                    if rebuilt_child:
                        new_elem.append(BeautifulSoup(rebuilt_child, "html.parser"))
                else:

                    text_content = str(child).strip()
                    if text_content:
                        new_elem.append(text_content)

            return str(new_elem)

        except Exception as e:
            logger.error(f"Error reconstructing content: {e}")
            return str(element) if element else ""

    def generate_payload(self, item: Dict, item_type: DepthLevel, additional_data: Dict = None) -> Dict:
        title, description = self.extract_content_from_file(item["href"], item_type)
        base_payload = {
            "name": title,
            "tags": [
                {"name": "Source", "value": "Confluence"},
                {"name": "Type", "value": str(item_type)},
            ]
        }

        match item_type:
            case DepthLevel.SHELF:
                base_payload.update({"description_html": description, "books": []})
            case DepthLevel.BOOK | DepthLevel.CHAPTER:
                base_payload["description_html"] = description
            case DepthLevel.PAGE:
                base_payload["html"] = description
        if additional_data:
            base_payload.update(additional_data)

        return base_payload, title
