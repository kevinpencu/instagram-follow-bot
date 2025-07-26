from selenium import webdriver
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from app.selenium_utils import navigate_to
from app.logger import get_logger
from selenium.common.exceptions import (
    TimeoutException,
)
from enum import Enum


class OperationState(Enum):
    AlreadyFollowed = 0
    FollowedOrRequested = 1
    FailedToFollow = 2
    AccountIsSuspended = 3
    FollowBlocked = 4


def go_to_user(driver: webdriver.Chrome, username: str):
    navigate_to(driver, f"https://instagram.com/{username}")


def is_account_suspended(driver: webdriver.Chrome):
    return "/accounts/suspended" in driver.current_url


def is_page_followed_or_requested(driver: webdriver.Chrome):
    return (
        len(
            driver.find_elements(
                By.XPATH,
                "//div[text()='Following'] | //div[text()='Requested']",
            )
        )
        > 0
    )


def follow_current_user(driver: webdriver.Chrome, username: str):
    elems = driver.find_elements(By.XPATH, "//div[text()='Follow']")
    if not elems:
        get_logger().error(
            f"[INSTA-SELENIUM]: Following {username} button not found"
        )
        return False

    get_logger().info(
        f"[INSTA-SELENIUM]: Following {username} button triggering"
    )
    elems[0].click()

    return True


def run_follow_action(driver: webdriver.Chrome, username: str):
    get_logger().info(f"[INSTA-SELENIUM]: Navigating to user {username}")
    go_to_user(driver, username)

    get_logger().info(
        f"[INSTA-SELENIUM]: Checking if account is suspended..."
    )
    if is_account_suspended(driver):
        get_logger().error(
            f"[INSTA-SELENIUM]: Account is suspended. Abandoning..."
        )
        return OperationState.AccountIsSuspended

    get_logger().info(
        f"[INSTA-SELENIUM]: Checking if page is already followed or requested..."
    )

    if is_page_followed_or_requested(driver):
        get_logger().info(
            f"[INSTA-SELENIUM]: Page is already followed or requested. Abandoning..."
        )
        return OperationState.AlreadyFollowed

    get_logger().info(f"[INSTA-SELENIUM]: Following user...")

    followed = follow_current_user(driver, username)
    if not followed:
        return OperationState.FailedToFollow

    time.sleep(3)
    if is_page_followed_or_requested(driver):
        return OperationState.FollowedOrRequested

    return OperationState.FollowBlocked
