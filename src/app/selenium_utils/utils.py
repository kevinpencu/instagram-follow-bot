from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import time
from app.constants import SELENIUM_WAIT_DELAY


def close_tabs(driver: webdriver.Chrome):
    windows = driver.window_handles
    if len(windows) == 1:
        return

    for i in range(1, len(windows)):
        driver.switch_to.window(windows[i])
        driver.close()

    driver.switch_to.window(driver.window_handles[0])


def navigate_to(driver: webdriver.Chrome, url: str):
    driver.get(url)
    time.sleep(SELENIUM_WAIT_DELAY)


def wait_page_loaded(driver: webdriver.Chrome):
    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script("return document.readyState")
        == "complete"
    )
