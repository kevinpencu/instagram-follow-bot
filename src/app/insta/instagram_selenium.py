from selenium import webdriver
from app.insta.enums.checkpoint import Checkpoint
from app.insta.checkpoint_conditions import CONDITIONS
from app.insta.checkpoint_bypass import BYPASSES
from app.insta.actions import FOLLOW_ACTION
from app.selenium_utils.utils import navigate_to


class InstagramWrapper:
    driver: webdriver.Chrome

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def get_cp(self, before_action: bool = False) -> Checkpoint:
        for cond in CONDITIONS.keys():
            if CONDITIONS[cond].is_active(self.driver):
                return CONDITIONS[cond].get_cp(before_action)
        return None

    def bypass_cp(self, cp: Checkpoint) -> bool:
        if cp in BYPASSES:
            return BYPASSES[cp].do_bypass()
        return False

    def visit_user_page(self, target: str):
        navigate_to(self.driver, f"https://instagram.com/{target}")

    def follow_action(self, target: str) -> Checkpoint:
        self.visit_user_page(target)

        cp = self.get_cp(True)
        if cp is not None:
            if self.bypass_cp(cp) is False:
                return cp

        FOLLOW_ACTION.run(self.driver)

        cp = self.get_cp()
        if cp is None:
            return Checkpoint.FollowBlocked

        return cp
