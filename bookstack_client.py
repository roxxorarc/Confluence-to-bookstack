import requests
from typing import Dict, Tuple
from utils import logger


class BookStackClient:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Authorization": f'Token {getattr(config, "BOOKSTACK_API_ID", "")}:{getattr(config, "BOOKSTACK_API_SECRET", "")}'
        }
        
    def test_endpoints(self):
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
                logger.error(f"API returned unexpected status code {response.status_code}: {response.text}")
                exit(1)

        except Exception as e:
            logger.error(f"Unexpected error while testing endpoints: {e}")

    def request(self, method: str, endpoint: str, data: Dict = None, files: Dict = None) -> Tuple[bool, Dict]:
        url = f"{self.config.BOOKSTACK_URL}{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, headers=self.headers, files=files, data=data)
                else:
                    response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            if response.status_code in [200, 201, 204]:
                if response.status_code == 204:
                    return True, {}
                return True, response.json()
            else:
                return False, {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text,
                }

        except Exception as e:
            return False, {"error": str(e)}

    def clear_content(self) -> Dict[str, int]:
        logger.info("Clearing existing BookStack content")
        deleted_objects = {"shelf": 0, "book": 0}
        
        targets = [
            ("shelf", "/shelves"),
            ("book", "/books")
        ]

        for name, endpoint in targets:
            success, response = self.request("GET", endpoint)
            if not success:
                logger.error(f"Failed to retrieve {name}s: {response}")
                continue
                
            items = response.get("data", [])
            logger.info(f"Found {len(items)} {name}s to delete")
            
            for item in items:
                item_id = item.get("id")
                item_name = item.get("name", "Unknown")
                if item_id:
                    success, _ = self.request("DELETE", f"{endpoint}/{item_id}")
                    if success:
                        logger.info(f"Deleted {name}: '{item_name}' (ID: {item_id})")
                        deleted_objects[name] += 1
                    else:
                        logger.error(f"Failed to delete {name} '{item_name}'")
        
        return deleted_objects
