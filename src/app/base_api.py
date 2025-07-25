import requests as re


class BaseApi:
    def __init__(self, apiUrl: str, headers: dict):
        self.apiUrl = apiUrl
        self.headers = headers
        pass

    def get(self, endpoint: str, params: dict = {}):
        return re.get(f"{self.apiUrl}{endpoint}", params=params)

    def post(self, endpoint: str, payload: dict):
        return re.post(f"{self.apiUrl}{endpoint}", data=payload)
