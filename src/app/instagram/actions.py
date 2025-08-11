import time
from selenium.webdriver.common.by import By
from selenium import webdriver
from dataclasses import dataclass
from app.core.logger import get_logger
from app.core.constants import FOLLOW_ACTION_DELAY
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
                if all:
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


FOLLOW_ACTION = Action(
    xpath_queries=["//div[text()='Follow']"],
    sleep=FOLLOW_ACTION_DELAY,
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
