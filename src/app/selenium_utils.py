from selenium import webdriver


def close_tabs(driver: webdriver.Chrome):
    windows = driver.window_handles
    if len(windows) == 1:
        return

    for i in range(1, len(windows)):
        driver.switch_to.window(windows[i])
        driver.close()


def wait_for_page_load(driver: webdriver.Chrome, timeout=10):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState")
        == "complete"
    )


def navigate_to(driver: webdriver.Chrome, url: str):
    driver.get("https://instagram.com")
    wait_for_page_load(driver)
    pass
