import time
from selenium.webdriver.common.by import By
from selenium import webdriver
from dataclasses import dataclass
from app.logger import get_logger


@dataclass
class Action:
    xpath_query: str
    sleep: float

    def run(self, driver: webdriver.Chrome) -> bool:
        elems = driver.find_elements(By.XPATH, self.xpath_query)
        if len(elems) <= 0:
            return False

        try:
            elems[0].click()
            time.sleep(self.sleep)
            return True
        except Exception as e:
            get_logger().error(f"Failed to run click: {str(e)}")

        return False


FOLLOW_ACTION = Action("//div[text()='Follow']", 3)
