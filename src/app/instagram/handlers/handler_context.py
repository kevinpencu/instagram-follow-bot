from dataclasses import dataclass
from app.airtable.models.profile import Profile
from selenium import webdriver


@dataclass
class HandlerContext:
    profile: Profile
    driver: webdriver.Chrome
    processed_targets: list[str]
    target: str
