import time
import random
from selenium.webdriver.common.by import By
from selenium import webdriver
from dataclasses import dataclass
from app.core.logger import get_logger
from app.core.constants import (
    FOLLOW_ACTION_DELAY_MINIMUM,
    FOLLOW_ACTION_DELAY_MAXIMUM,
)
from app.instagram.checkpoint_conditions import (
    Checkpoint,
    logged_in_condition,
    CheckpointCondition,
)


@dataclass
class Action:
    xpath_queries: list[str]
    sleep: float = 0
    all: bool = False

    def run(self, driver: webdriver.Chrome) -> bool:
        for xpath_query in self.xpath_queries:
            elems = driver.find_elements(By.XPATH, xpath_query)
            if len(elems) <= 0:
                return False

            try:
                if self.all:
                    for x in elems:
                        x.click()
                        time.sleep(self.sleep)
                else:
                    elems[0].click()
                    time.sleep(self.sleep)
            except Exception as e:
                get_logger().error(f"Failed to run click: {str(e)}")
                return False

        return True


class AcceptRequestsAction(Action):
    accepted_users: list[str]

    def __init__(self):
        super().__init__([])
        self.accepted_users = []

    def run(self, driver: webdriver.Chrome) -> bool:
        notifications_btn = driver.find_elements(By.XPATH, "//span[text()='Notifications']")
        if len(notifications_btn) <= 0:
            return False

        notifications_btn[0].click()
        time.sleep(7)

        follow_requests_btn = driver.find_elements(By.XPATH, "//span[text()='Follow requests']")
        if len(follow_requests_btn) <= 0:
            return True

        follow_requests_btn[0].click()
        time.sleep(4)

        confirm_btns = driver.find_elements(By.XPATH, "//div[text()='Confirm']")
        if len(confirm_btns) <= 0:
            return True

        for confirm_btn in confirm_btns:
            main_container = confirm_btn.find_elements(By.XPATH, "../../..")
            if len(main_container) <= 0:
                continue

            children_of_main = main_container[0].find_elements(By.XPATH, "./*")
            if len(children_of_main) <= 1:
                continue

            name_container = children_of_main[1]
            link_tag = name_container.find_elements(By.XPATH, "./*")
            if len(link_tag) <= 0:
                continue

            username = link_tag[0].find_elements(By.XPATH, "./*")
            if len(username) <= 0:
                continue

            username_value = username[0].text
            if len(username_value) <= 0:
                continue

            self.accepted_users.append(username_value)

            confirm_btn.click()
            time.sleep(2.5)

        return True


@dataclass
class ActionChain:
    preconditions: list[CheckpointCondition]
    actions: list[Action]

    def meets_conditions(self, driver: webdriver.Chrome) -> bool:
        return all(a.is_active(driver) for a in self.preconditions)

    def run(self, driver: webdriver.Chrome) -> bool:
        if self.meets_conditions(driver) is False:
            return False

        return all(a.run(driver) for a in self.actions)


def create_follow_action() -> Action:
    dynamic_delay = random.uniform(FOLLOW_ACTION_DELAY_MINIMUM, FOLLOW_ACTION_DELAY_MAXIMUM)
    return Action(
        xpath_queries=["//button[.//div[normalize-space(text())='Follow']]"],
        sleep=dynamic_delay,
        all=False,
    )


ACCEPT_FOLLOW_REQUESTS_CHAIN = ActionChain(
    preconditions=[logged_in_condition],
    actions=[
        Action(
            xpath_queries=["//span[text()='Notifications']"],
            sleep=3,
            all=False,
        ),
        Action(
            xpath_queries=["//span[text()='Follow requests']"],
            sleep=3,
            all=False,
        ),
        Action(
            xpath_queries=["//div[text()='Confirm']"], all=True, sleep=1
        ),
    ],
)
