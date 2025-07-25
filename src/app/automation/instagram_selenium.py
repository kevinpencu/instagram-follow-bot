from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from app.selenium_utils import navigate_to


def go_to_base_sync(driver: webdriver.Chrome):
    if "instagram.com" in driver.current_url:
        return
    navigate_to("https://instagram.com")


def go_to_user(driver: webdriver.Chrome, username: str):
    if username.lower() in driver.current_url:
        return
    navigate_to(driver, f"https://instagram.com/{username}")


def is_account_suspended(driver: webdriver.Chrome):
    go_to_base_sync(driver)

    # TODO(HSO): Ask Vik for a suspended instagram AdsPower session
    # To have a more detailed implementation
    return "/accounts/suspended" in driver.current_url


def is_account_followblocked(driver: webdriver.Chrome):
    page_source = self.driver.page_source.lower()
    follow_block_indicators = [
        "try again later",
        "action blocked",
        "we restrict certain activity",
        "temporarily blocked",
        "slow down",
        "too many requests",
    ]

    for x in indicators:
        if x in page_source:
            return True

    return False


def is_page_public(driver: webdriver.Chrome):
    page_source = self.driver.page_source.lower()
    indicators = [
        "this account is private",
        "only approved followers can see",
        "follow to see their photos and videos",
        "this account is private.",
        "account is private",
    ]

    for x in indicators:
        if x in page_source:
            return False

    return True


def is_page_followed_or_requested(driver: webdriver.Chrome):
    success_selectors = [
        "//button[text()='Following']",
        "//button[text()='Requested']",
        "//button[contains(text(), 'Following') and not(contains(text(), 'Follow '))]",
        "//button[contains(text(), 'Requested')]",
        "//*[contains(@class, 'button') and text()='Following']",
        "//*[contains(@class, 'button') and text()='Requested']",
    ]

    for selector in success_selectors:
        try:
            success_button = self.driver.find_element(By.XPATH, selector)
            if success_button and success_button.is_displayed():
                return True
        except Exception as e:
            pass

    return False


def follow_user(driver: webdriver.Chrome, username: str):
    pass
