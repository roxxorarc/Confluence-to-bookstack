import os
from typing import Optional, Tuple
from bs4 import BeautifulSoup, Tag
from utils import image_to_data_url, is_image_file, logger, DepthLevel, title_to_slug


class ContentProcessor:
    def __init__(self, config, api_client):
        self.config = config
        self.api_client = api_client
        self.uploaded_attachments = {}
        self.errors = []

    def is_attachment_uploaded(self, page_id: str, file_path: str) -> bool:
        return page_id in self.uploaded_attachments and file_path in self.uploaded_attachments[page_id]
    
    def mark_attachment_uploaded(self, page_id: str, file_path: str, attachment_id: str):
        if page_id not in self.uploaded_attachments:
            self.uploaded_attachments[page_id] = {}
        self.uploaded_attachments[page_id][file_path] = attachment_id

    def upload_attachment(self, file_path: str, filename: str, page_id: str) -> Optional[str]:
        if self.is_attachment_uploaded(page_id, file_path):
            logger.debug(f"Attachment already uploaded: {filename}")
            return self.uploaded_attachments[page_id][file_path]
        
        if not os.path.exists(file_path):
            logger.warning(f"Attachment file not found: {file_path}")
            self.errors.append((filename, "File not found"))
            return None
        
        try:
            with open(file_path, "rb") as file:
                files = {'file': (filename, file)}
                upload_data = {
                    "name": filename,
                    "uploaded_to": page_id
                }
                success, response_data = self.api_client.request("POST", "/attachments", data=upload_data, files=files)
            
            if success:
                attachment_id = response_data.get("id")
                self.mark_attachment_uploaded(page_id, file_path, attachment_id)
                return attachment_id
            else:
                logger.error(f"Failed to upload attachment {filename}: {response_data}")
                self.errors.append((filename, response_data))
                return None
                
        except Exception as e:
            logger.error(f"Error uploading attachment {filename}: {e}")
            self.errors.append((filename, str(e)))
            return None

    def process_inline_pdf(self, element: Tag, page_id: Optional[str] = None):
        if not page_id:
            return
            
        container_id = element.get("data-linked-resource-container-id", "")
        resource_id = element.get("data-linked-resource-id", "")
        default_alias = element.get("data-linked-resource-default-alias", "")
        file_path = f"{self.config.SOURCE_PATH}/attachments/{container_id}/{resource_id}.pdf"
        filename = default_alias or f"{resource_id}.pdf"
        
        attachment_id = self.upload_attachment(file_path, filename, page_id)
        if attachment_id:
            canvas_html = f'<p><canvas data-pdfurl="/attachments/{attachment_id}"></canvas>&nbsp;</p>'
            canvas_soup = BeautifulSoup(canvas_html, "html.parser")
            return canvas_soup

    def process_inline_img(self, element: Tag, page_id: Optional[str] = None):
        file_path = self.config.SOURCE_PATH + "/" + element["src"]
        if element["src"].startswith(("data:", "http://", "https://")) or not page_id or not is_image_file(file_path):
            return    
        try:
            image_data_url = image_to_data_url(file_path)
            element["src"] = image_data_url
        except Exception as e:
            logger.error(f"Error processing image attachment {file_path}: {e}")
            self.errors.append((file_path, str(e)))

    def process_greybox_attachments(self, soup: BeautifulSoup, page_id: Optional[str] = None):
        greybox_divs = soup.find_all("div", class_="greybox")
        if not page_id or not greybox_divs:
            return
        for greybox in greybox_divs:
            attachment_links = greybox.find_all("a", href=True)
            
            for link in attachment_links:
                href = link.get("href", "")
                if not href.startswith("attachments/"):
                    continue
                filename = link.get_text(strip=True)
                file_path = f"{self.config.SOURCE_PATH}/{href}"
                self.upload_attachment(file_path, filename, page_id)

    def extract_content_from_file(self, file_path: str, item_type: DepthLevel, page_id: Optional[str] = None) -> Tuple[str, str]:
        full_path = self.config.SOURCE_PATH + "/" + file_path
        try:
            with open(full_path, "r", encoding="utf-8") as file:
                content = file.read()
        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")
            self.errors.append((full_path, str(e)))
            return "", ""
        soup = BeautifulSoup(content, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        description = ""
        if item_type == DepthLevel.PAGE:
            main_content = soup.select_one("div#main-content")
            if main_content:
                description = self.reconstruct_dom_content(main_content, page_id)
            if page_id:
                self.process_greybox_attachments(soup, page_id)
        return title, description

    def reconstruct_dom_content(self, element: Tag, page_id: Optional[str] = None) -> str:
        if not element:
            return ""
        try:
            canvas = None
            if element.name is None:
                return element.string.strip() if element.string else ""
            if element.name == "img" and element.get("data-linked-resource-content-type", "").startswith("image"):
                self.process_inline_img(element, page_id)
            elif element.name == "a" and element.get("data-nice-type", "").startswith("PDF"):
                canvas = self.process_inline_pdf(element, page_id)
                print(canvas)
            elif element.name == "a" and element.has_attr("href"):
                href = element["href"]
                if href.endswith(".html") and not href.startswith(("http://", "https://", "mailto:", "#")):
                    self.process_internal_link(element, href)
            
            IMPORTANT_ATTRS = frozenset([
                "id", "style", "href", "src", "title", "colspan", "rowspan"
            ]) 
            new_soup = BeautifulSoup("", "html.parser")
            new_elem = new_soup.new_tag(element.name)
            for attr in IMPORTANT_ATTRS:
                if element.has_attr(attr):
                    new_elem[attr] = element[attr]  
            for child in element.contents:
                if hasattr(child, "name"):
                    rebuilt_child = self.reconstruct_dom_content(child, page_id)
                    if rebuilt_child:
                        new_elem.append(BeautifulSoup(rebuilt_child, "html.parser"))
                else:
                    text_content = str(child).strip()
                    if text_content:
                        new_elem.append(text_content)
            if canvas:
                new_elem.append(canvas)
            return str(new_elem)
        except Exception as e:
            logger.error(f"Error reconstructing content: {e}")
            self.errors.append((str(element), str(e)))
            return str(element) if element else ""

    def process_internal_link(self, element: Tag, href: str):
        file_path = os.path.join(self.config.SOURCE_PATH, href)
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                soup = BeautifulSoup(content, "html.parser")
                title = soup.title.get_text(strip=True)
                element["href"] = title_to_slug(title)
            else:
                logger.warning(f"Internal link file not found: {file_path}")
                self.errors.append((file_path, "File not found for internal link"))
        except Exception as e:
            logger.error(f"Error processing internal link {href}: {e}")
            self.errors.append((href, str(e)))
            return None