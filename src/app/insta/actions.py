from app.insta.enums.checkpoint import Checkpoint
import time
from selenium.webdriver.common.by import By
from typing import Callable
from selenium import webdriver
from dataclasses import dataclass
import operator


@dataclass
class Action:
    xpath_query: str
    sleep: float

    def run(self, driver: webdriver.Chrome) -> bool:
        elems = driver.find_elements(By.XPATH, self.xpath_query)
        if len(elems) <= 0:
            return False

        elems[0].click()
        time.sleep(self.sleep)

        return True


FOLLOW_ACTION = Action("//div[text()='Follow']", 3)
