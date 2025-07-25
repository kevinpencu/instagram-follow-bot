from app.config import get_cfg
from pyairtable import Api
from dataclasses import dataclass
import requests

config = get_cfg()["airtable"]


@dataclass
class ProfileDataRow:
    ads_power_id: str
    username: str


def get_api():
    return Api(config["apiKey"])


def get_table():
    return get_api().table(config["baseId"], config["tableName"])


def get_profiles():
    return get_table().all(
        fields=["Targets", "AdsPower ID", "Username"], max_records=15
    )


def get_profiles_mapped() -> list[ProfileDataRow]:
    return [
        ProfileDataRow(
            x["fields"]["AdsPower ID"], x["fields"]["Username"]
        )
        for x in get_profiles()
    ]


def get_targets_download_urls(row: dict):
    fields = row.get("fields")
    return (
        [x["url"] for x in fields.get("Targets")]
        if fields.get("Targets") is not None
        and len(fields.get("Targets")) > 0
        else []
    )


def fetch_and_parse_usernames(row: dict) -> list[str]:
    downloads = []

    for link in get_targets_download_urls(row):
        resp = requests.get(link)
        if resp.status_code != 200:
            continue
        downloads.append(resp.text)

    usernames = []

    for x in downloads:
        for username in x.splitlines():
            if len(username.strip()) <= 0:
                continue
            usernames.append(username)

    return usernames
