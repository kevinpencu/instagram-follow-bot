import requests as re
from app.logger import get_logger


class BaseApi:
    def __init__(self, apiUrl: str, headers: dict):
        self.apiUrl = apiUrl
        self.headers = headers
        pass

    def get(self, endpoint: str, params: dict = {}):
        try:
            return re.get(
                f"{self.apiUrl}{endpoint}", params=params, timeout=90
            )
        except re.exceptions.RequestException as e:
            get_logger().error(
                f"[BASE-API]: GET request failed for {endpoint}: {str(e)}"
            )
            raise

    def post(self, endpoint: str, payload: dict):
        try:
            return re.post(
                f"{self.apiUrl}{endpoint}", data=payload, timeout=90
            )
        except re.exceptions.RequestException as e:
            get_logger().error(
                f"[BASE-API]: POST request failed for {endpoint}: {str(e)}"
            )
            raise
