from app.config import get_cfg
from pyairtable import Api
from dataclasses import dataclass
from app.logger import get_logger
import requests

config = get_cfg()["airtable"]


@dataclass
class ProfileDataRow:
    airtable_id: str
    ads_power_id: str
    username: str
    target_download_urls: list[str]
    processed_targets_download_urls: list[str]


def get_api():
    return Api(config["apiKey"])


def get_table():
    return get_api().table(config["baseId"], config["tableName"])


def get_profiles():
    table = get_table()
    all_records = []

    for batch in table.iterate(
        fields=[
            "Targets",
            "AdsPower ID",
            "Username",
            "ProcessedTargetsTextFile",
        ],
        view=config["viewId"],
        page_size=100,
    ):
        all_records.extend(batch)

    get_logger().info(
        f"[AIRTABLE]: Fetched {len(all_records)} profile records"
    )
    return all_records


def get_targets_download_urls(row: dict):
    fields = row.get("fields")
    return (
        [x["url"] for x in fields.get("Targets")]
        if fields.get("Targets") is not None
        and len(fields.get("Targets")) > 0
        else []
    )


def get_processed_targets_download_urls(row: dict):
    fields = row.get("fields")
    return (
        [x["url"] for x in fields.get("ProcessedTargetsTextFile")]
        if fields.get("ProcessedTargetsTextFile") is not None
        and len(fields.get("ProcessedTargetsTextFile")) > 0
        else []
    )


def get_existing_processed_targets_filename(record: dict) -> str:
    """Get the filename of existing ProcessedTargetsTextFile attachment, if any"""
    fields = record.get("fields")
    processed_files = fields.get("ProcessedTargetsTextFile")

    if processed_files and len(processed_files) > 0:
        return processed_files[0].get(
            "filename",
            f"processed_targets_{fields.get('Username', 'unknown')}.txt",
        )

    return f"processed_targets_{fields.get('Username', 'unknown')}.txt"


def refresh_profile(row: ProfileDataRow) -> ProfileDataRow:
    table = get_table()

    try:
        record = table.get(row.airtable_id)
        get_logger().info(f"[AIRTABLE]: Refreshed profile {row.username}")

        return ProfileDataRow(
            record["id"],
            record["fields"]["AdsPower ID"],
            record["fields"]["Username"],
            get_targets_download_urls(record),
            get_processed_targets_download_urls(record),
        )
    except Exception as e:
        get_logger().error(
            f"[AIRTABLE]: Failed to refresh profile {row.username}: {e}"
        )

    return row


def get_profiles_mapped() -> list[ProfileDataRow]:
    return [
        ProfileDataRow(
            x["id"],
            x["fields"]["AdsPower ID"],
            x["fields"]["Username"],
            get_targets_download_urls(x),
            get_processed_targets_download_urls(x),
        )
        for x in get_profiles()
    ]


def fetch_and_parse_usernames(data: ProfileDataRow) -> list[str]:
    get_logger().info("[AIRTABLE]: Fetching & Parsing Usernames")
    downloads = []

    for link in data.target_download_urls:
        get_logger().info(f"[AIRTABLE]: Downloading {link}")
        resp = requests.get(link)
        if resp.status_code != 200:
            get_logger().error(f"[AIRTABLE]: Download Failed {link}")
            continue
        downloads.append(resp.text)

    usernames = []

    for x in downloads:
        for username in x.splitlines():
            if len(username.strip()) <= 0:
                continue
            usernames.append(username)

    return usernames


def fetch_and_parse_processed_targets(data: ProfileDataRow) -> list[str]:
    get_logger().info("[AIRTABLE]: Fetching & Parsing Processed Targets")
    downloads = []

    for link in data.processed_targets_download_urls:
        get_logger().info(f"[AIRTABLE]: Downloading {link}")
        resp = requests.get(link)
        if resp.status_code != 200:
            get_logger().error(f"[AIRTABLE]: Download Failed {link}")
            continue
        downloads.append(resp.text)

    usernames = []

    for x in downloads:
        for username in x.splitlines():
            if len(username.strip()) <= 0:
                continue
            usernames.append(username)

    return usernames


def update_processed_targets(
    row: ProfileDataRow, usernames: list[str]
) -> bool:
    table = get_table()

    try:
        record = table.get(row.airtable_id)
        filename = get_existing_processed_targets_filename(record)

        content = "\n".join(usernames)

        get_logger().info(
            f"[AIRTABLE]: Updating processed targets for {row.username} ({len(usernames)} usernames) using filename: {filename}"
        )

        # Delete existing attachment
        table.update(row.airtable_id, {"ProcessedTargetsTextFile": []})
        
        # Upload new attachment
        result = table.upload_attachment(
            record_id=row.airtable_id,
            field="ProcessedTargetsTextFile",
            filename=filename,
            content=content,
            content_type="text/plain",
        )

        get_logger().info(
            f"[AIRTABLE]: Successfully updated processed targets for {row.username}"
        )
        return True

    except Exception as e:
        get_logger().error(
            f"[AIRTABLE]: Failed to update processed targets for {row.username}: {e}"
        )
        return False
