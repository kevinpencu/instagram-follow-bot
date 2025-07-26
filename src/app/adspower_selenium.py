from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from app.selenium_utils import close_tabs
from app.adspower.api_wrapper import StartProfileResponse
from app.logger import get_logger


def run_selenium(
    start_profile_response: StartProfileResponse,
) -> webdriver.Chrome:
    try:
        options = Options()
        options.add_experimental_option(
            "debuggerAddress",
            f"127.0.0.1:{start_profile_response.debug_port}",
        )

        service = Service(start_profile_response.webdriver)

        driver = webdriver.Chrome(service=service, options=options)
        close_tabs(driver)

        return driver
    except Exception as e:
        get_logger().error(f"[ADSPOWER-SELENIUM]: Failed to create WebDriver: {str(e)}")
        raise
