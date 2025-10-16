from selenium import webdriver
import time
from app.instagram.enums.checkpoint import Checkpoint
from app.instagram.checkpoint_conditions import (
    CONDITIONS,
    logged_in_condition,
    is_page_private_condition,
)
from app.instagram.checkpoint_bypass import BYPASSES
from app.instagram.actions import (
    create_follow_action,
    AcceptRequestsAction,
    create_unfollow_action
)
from app.selenium_utils.utils import navigate_to
from app.core.logger import get_logger


class InstagramWrapper:
    driver: webdriver.Chrome

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def is_logged_in(self):
        return logged_in_condition.is_active(self.driver)

    def accept_follow_requests(self) -> list[str]:
        navigate_to(self.driver, f"https://instagram.com")
        time.sleep(2)
        if self.is_logged_in() is False:
            return None

        action = AcceptRequestsAction()
        if action.run(self.driver) is False:
            get_logger().error(
                "[INSTAWRAPPER]: Accepting requests failed"
            )
            return []
        get_logger().info("[INSTAWRAPPER]: Accepting requests success")
        return action.accepted_users

    def unfollow_user(self, user: str):
        create_unfollow_action(user).run(self.driver)

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
        get_logger().info(
            f"[INSTAWRAPPER, TARGET: {target}]: Processing Checkpoint: {cp}"
        )
        if cp is not None:
            if self.bypass_cp(cp) is False:
                get_logger().info(
                    f"[INSTAWRAPPER, TARGET: {target}]: Bypass for {cp} non-existing or failed"
                )
                return cp

        get_logger().info(
            f"[INSTAWRAPPER, TARGET: {target}]: Executing Follow Action..."
        )

        is_page_private = is_page_private_condition.is_active(self.driver)

        create_follow_action().run(self.driver)

        cp = self.get_cp()

        # Check for "Try Again Later" popup (complete follow block)
        if cp is Checkpoint.CompletelyFollowBlocked:
            return Checkpoint.CompletelyFollowBlocked

        # If no checkpoint detected after follow action
        if cp is None:
            # If this was a public account and follow button didn't change to Following/Requested,
            # it means we're blocked from following public accounts
            if is_page_private is False:
                get_logger().info(
                    f"[INSTAWRAPPER, TARGET: {target}]: No checkpoint after follow on public account - treating as PublicFollowBlocked"
                )
                return Checkpoint.PublicFollowBlocked
            # For private accounts, generic follow block
            return Checkpoint.FollowBlocked

        # Public follow block detection: Requested button on public account
        if cp is Checkpoint.PageRequested and is_page_private is False:
            return Checkpoint.PublicFollowBlocked

        return cp
