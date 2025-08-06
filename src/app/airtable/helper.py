from app.config import get_cfg
import requests
from pyairtable import Api

config = get_cfg()["airtable"]


def get_api():
    return Api(config["apiKey"])


def get_table():
    return get_api().table(config["baseId"], config["tableName"])


def map_attachment_field_to_urls(attachment_field: dict) -> list[str]:
    if attachment_field is None:
        return []

    return (
        [x["url"] for x in attachment_field]
        if attachment_field is not None and len(attachment_field) > 0
        else []
    )


def download_and_parse_lines_from_url(urls: list[str]) -> list[str]:
    downloads = []

    for link in urls:
        resp = requests.get(link)
        if resp.status_code != 200:
            continue
        downloads.append(resp.text)

    lines = []

    for x in downloads:
        for line in x.splitlines():
            if len(line.strip()) <= 0:
                continue
            lines.append(line)

    return lines
