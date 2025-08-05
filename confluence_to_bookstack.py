import os
from typing import Dict, Tuple
from bs4 import BeautifulSoup
import requests
from utils import logger, DepthLevel

class ConfluenceToBookstack:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Authorization": f'Token {getattr(config, "BOOKSTACK_API_ID", "")}:{getattr(config, "BOOKSTACK_API_SECRET", "")}'
        }

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
        for root, dirs, files in os.walk(self.config.SOURCE_PATH):
            if "index.html" in files:
                index_file = os.path.join(root, "index.html")

        logger.info(f"Found index.html at {index_file}")
        parsed_data = self.parse_index_html(index_file)
        if parsed_data and "hierarchy" in parsed_data:
            logger.debug(f"Parsed hierarchy: {parsed_data['hierarchy']}")

        self.print_report()

    def print_report(self):
        pass
