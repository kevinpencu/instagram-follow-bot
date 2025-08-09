from app.config import get_cfg
from app.adspower.base_api import BaseApi
from app.logger import get_logger
from dataclasses import dataclass

config = get_cfg()["adspower"]


@dataclass
class StartProfileResponse:
    debug_port: int
    webdriver: str
    url: str


class AdsPowerApi(BaseApi):
    def __init__(self):
        BaseApi.__init__(
            self, config["apiUrl"], {"api_key": config["apiKey"]}
        )

    def check_health(self):
        ok = False
        details = ""

        try:
            ok = self.get("/user/list").ok
        except Exception as e:
            details = str(e)
            pass

        if not ok:
            get_logger().fatal(f"[ADSPOWER]: API Not OK\n{details}\n")

        return ok

    def start_profile(self, user_id: str) -> StartProfileResponse:
        payload = {
            "user_id": user_id,
            "launch_args": "",
            "headless": 0,
            "disable_password_filling": 0,
            "clear_cache_after_closing": 0,
            "enable_password_saving": 0,
        }

        json = self.get("/browser/active", payload).json()
        if json.get("code") != 0:
            get_logger().error(
                "[ADSPOWER]: Failed to start profile via check status. Testing via browser start."
            )
            get_logger().error(f"[ADSPOWER]: {json}")

        json = self.get("/browser/start", payload).json()
        if json.get("code") != 0:
            get_logger().error(
                "[ADSPOWER]: Failed to start profile via browser start. Abandoning"
            )
            get_logger().error(f"[ADSPOWER]: {json}")
            return None

        return StartProfileResponse(
            debug_port=json["data"]["debug_port"],
            webdriver=json["data"]["webdriver"],
            url=json["data"]["ws"]["selenium"],
        )

    def stop_profile(self, user_id: str):
        return self.get("/browser/stop", params={"user_id": user_id})


adspower = AdsPowerApi()
