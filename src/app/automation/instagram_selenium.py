from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from app.selenium_utils import navigate_to, wait_page_loaded
from app.logger import get_logger
from app.airtable.models.profile import Profile
from enum import Enum


class OperationState(Enum):
    AlreadyFollowed = 0
    FollowedOrRequested = 1
    FailedToFollow = 2
    AccountIsSuspended = 3
    FollowBlocked = 4
    AccountLoggedOut = 5
    PageUnavailable = 6
    AccountBanned = 7
    AutomaticBehaviourSuspected = 8
    SomethingWentWrongCheckpoint = 9
    YourAccountWasCompromised = 10
    BadProxy = 11
    SaveLoginInfo = 12


def go_to_user(driver: webdriver.Chrome, username: str):
    navigate_to(driver, f"https://instagram.com/{username}")


def is_account_suspended(driver: webdriver.Chrome):
    return "/accounts/suspended" in driver.current_url


def is_account_banned(driver: webdriver.Chrome):
    return "/accounts/disabled" in driver.current_url


def is_automatic_behaviour_suspected(driver: webdriver.Chrome):
    return (
        len(
            driver.find_elements(
                By.XPATH,
                "//*[text()='We suspect automated behavior on your account']",
            )
        )
        > 0
    )


def is_http_429_chrome(driver: webdriver.Chrome) -> bool:
    elems = driver.find_elements(
        By.XPATH,
        "//span[text()='This page isn’t working'] | //div[text()='HTTP ERROR 429']",
    )
    return len(elems) >= 2


def is_save_login_info(driver: webdriver.Chrome) -> bool:
    elems = driver.find_elements(
        By.XPATH,
        "//*[text()='Save info']",
    )
    return len(elems) > 0


def bypass_save_login_info(
    driver: webdriver.Chrome, username: str
) -> bool:
    if is_save_login_info(driver) is False:
        return True

    elems = driver.find_elements(
        By.XPATH,
        "//*[text()='Save info']",
    )

    elems[0].click()
    wait_page_loaded(driver)

    go_to_user(driver, username)

    return is_save_login_info(driver) is False


def bypass_automatic_behaviour_suspected(
    driver: webdriver.Chrome, username: str
):
    if is_automatic_behaviour_suspected(driver) is False:
        return True

    elems = driver.find_element(By.XPATH, "//*[text()='Dismiss']")

    if len(elems) <= 0:
        return True

    elems[0].click()

    wait_page_loaded(driver)
    go_to_user(driver, username)

    return is_automatic_behaviour_suspected(driver) is False


def is_something_went_wrong_checkpoint(driver: webdriver.Chrome):
    return (
        len(
            driver.find_elements(
                By.XPATH,
                "//h3[text()='Something went wrong'] | //div[text()='Reload page']",
            )
        )
        == 2
    )


def bypass_something_went_wrong_checkpoint(
    driver: webdriver.Chrome, username: str
):
    if is_something_went_wrong_checkpoint(driver) is False:
        return True

    elems = driver.find_elements(By.XPATH, "//div[text()='Reload page']")

    if len(elems) <= 0:
        return True

    elems[0].click()

    wait_page_loaded(driver)
    go_to_user(driver, username)

    return is_something_went_wrong_checkpoint(driver) is False


def is_your_account_was_compromised(driver: webdriver.Chrome):
    return (
        len(
            driver.find_elements(
                By.XPATH,
                "//h3[text()='Your Account Was Compromised'] | //div[text()='Change Password']",
            )
        )
        == 2
    )


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
    time.sleep(3)

    return True


def is_page_unavailable(driver: webdriver.Chrome):
    elems = driver.find_elements(
        By.XPATH, '//span[text()="Sorry, this page isn\'t available."]'
    )
    if not elems:
        return False

    return True


def is_logged_out(driver: webdriver.Chrome):
    # Check for possible elements indicating profile is logged out
    login_buttons = driver.find_elements(
        By.XPATH,
        "//div[@role='button' and text()='Log in'] | //div[text()='Log in'] | //div[text()='Sign up for Instagram'] | //button[text()='Log In']",
    )

    return len(login_buttons) > 0


def run_accept_requests_action(
    driver: webdriver.Chrome, profile: Profile
):
    get_logger().info(
        f"[INSTA-SELENIUM]: Starting Accept Requests Action for profile {profile.username}..."
    )
    pass


def run_follow_action(driver: webdriver.Chrome, username: str):
    get_logger().info(f"[INSTA-SELENIUM]: Navigating to user {username}")
    go_to_user(driver, username)

    get_logger().info(
        "[INSTA-SELENIUM]: Checking if account is logged out..."
    )

    if is_logged_out(driver):
        get_logger().error(
            "[INSTA-SELENIUM]: Account is logged out. Abandoning..."
        )
        return OperationState.AccountLoggedOut

    get_logger().info(
        "[INSTA-SELENIUM]: Checking if account is suspended..."
    )
    if is_account_suspended(driver):
        get_logger().error(
            "[INSTA-SELENIUM]: Account is suspended. Abandoning..."
        )
        return OperationState.AccountIsSuspended

    get_logger().info(
        "[INSTA-SELENIUM]: Checking if account is banned..."
    )
    if is_account_banned(driver):
        get_logger().error(
            "[INSTA-SELENIUM]: Account is banned. Abandoning..."
        )
        return OperationState.AccountBanned

    get_logger().info(
        "[INSTA-SELENIUM]: Checking if account is flagged as compromised / change password..."
    )
    if is_your_account_was_compromised(driver):
        get_logger().error(
            "[INSTA-SELENIUM]: Account marked as compromised / Change Password. Abandoning..."
        )
        return OperationState.YourAccountWasCompromised

    if is_http_429_chrome(driver):
        get_logger().error(
            "[INSTA-SELENIUM]: Bad Proxy Detected. Abandoning..."
        )
        return OperationState.BadProxy

    get_logger().info(
        "[INSTA-SELENIUM]: Checking if page is already followed or requested..."
    )
    if is_page_followed_or_requested(driver):
        get_logger().info(
            "[INSTA-SELENIUM]: Page is already followed or requested. Abandoning..."
        )
        return OperationState.AlreadyFollowed

    if is_page_unavailable(driver):
        get_logger().info(
            "[INSTA-SELENIUM]: Page is unavailable. Abandoning..."
        )
        return OperationState.PageUnavailable

    if bypass_automatic_behaviour_suspected(driver, username) is False:
        get_logger().info(
            "[INSTA-SELENIUM]: Automatic behaviour suspected, failed to bypass. Abandoning..."
        )
        return OperationState.AutomaticBehaviourSuspected

    if bypass_save_login_info(driver, username) is False:
        get_logger().info(
            "[INSTA-SELENIUM]: Save Login Info, failed to bypass. Abandoning..."
        )
        return OperationState.SaveLoginInfo

    if bypass_something_went_wrong_checkpoint(driver, username) is False:
        get_logger().info(
            "[INSTA-SELENIUM]: Someting went wrong checkpoint, failed to bypass. Abandoning..."
        )
        return OperationState.SomethingWentWrongCheckpoint

    get_logger().info("[INSTA-SELENIUM]: Following user...")

    followed = follow_current_user(driver, username)
    if not followed:
        return OperationState.FailedToFollow

    time.sleep(3)
    if is_page_followed_or_requested(driver):
        return OperationState.FollowedOrRequested

    get_logger().info(
        "[INSTA-SELENIUM]: Follow didn't work, checking if account is logged out..."
    )
    if is_logged_out(driver):
        get_logger().error(
            "[INSTA-SELENIUM]: Account is logged out (detected after follow attempt). Abandoning..."
        )
        return OperationState.AccountLoggedOut

    get_logger().info(
        "[INSTA-SELENIUM]: Follow didn't work and not logged out - marking as follow blocked"
    )
    return OperationState.FollowBlocked
