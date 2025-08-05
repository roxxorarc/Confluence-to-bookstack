from typing import Dict, Tuple
import requests
from utils import logger

class ConfluenceToBookstack:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Authorization": f'Token {getattr(config, "BOOKSTACK_API_ID", "")}:{getattr(config, "BOOKSTACK_API_SECRET", "")}'
        }

    def run(self):
        self.test_bookstack_endpoints()

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
