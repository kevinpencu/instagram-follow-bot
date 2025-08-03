from app.config import get_cfg
from pyairtable import Api
from dataclasses import dataclass
from app.logger import get_logger
import requests
from datetime import datetime, timezone

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
            "Already Followed",
        ],
        view=config["viewId"],
        page_size=100,
    ):
        all_records.extend(batch)

    get_logger().info(
        f"[AIRTABLE]: Fetched {len(all_records)} profile records"
    )

    # Debug: Log the first record to see its structure
    if all_records:
        get_logger().debug(
            f"[AIRTABLE]: First record fields: {list(all_records[0].get('fields', {}).keys())}"
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
        [x["url"] for x in fields.get("Already Followed")]
        if fields.get("Already Followed") is not None
        and len(fields.get("Already Followed")) > 0
        else []
    )


def get_existing_processed_targets_filename(record: dict) -> str:
    fields = record.get("fields")
    processed_files = fields.get("Already Followed")

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

        result = table.upload_attachment(
            record_id=row.airtable_id,
            field="Already Followed",
            filename=filename,
            content=content,
            content_type="text/plain",
        )

        updated_record = table.get(row.airtable_id)
        processed_files = updated_record.get("fields", {}).get(
            "Already Followed", []
        )

        if len(processed_files) > 1:
            table.update(
                row.airtable_id,
                {"Already Followed": [processed_files[-1]]},
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


def update_status(row: ProfileDataRow, status: str) -> bool:
    """Update the Status field for a profile in Airtable"""
    table = get_table()

    try:
        get_logger().info(
            f"[AIRTABLE]: Updating status for {row.username} to '{status}'"
        )

        # Status is a multi-select field, so we need to pass an array
        result = table.update(row.airtable_id, {"Status": [status]})

        get_logger().info(
            f"[AIRTABLE]: Successfully updated status for {row.username} to '{status}'"
        )
        return True

    except Exception as e:
        get_logger().error(
            f"[AIRTABLE]: Failed to update status for {row.username}: {e}"
        )
        return False


def update_follow_limit_reached(row: ProfileDataRow) -> bool:
    """Update the 'Reached Follow Limit' field with current UTC timestamp"""
    table = get_table()

    try:
        current_utc = datetime.now(timezone.utc).isoformat()

        get_logger().info(
            f"[AIRTABLE]: Updating 'Reached Follow Limit' for {row.username} with timestamp {current_utc}"
        )

        result = table.update(
            row.airtable_id, {"Reached Follow Limit": current_utc}
        )

        get_logger().info(
            f"[AIRTABLE]: Successfully updated 'Reached Follow Limit' for {row.username}"
        )
        return True

    except Exception as e:
        get_logger().error(
            f"[AIRTABLE]: Failed to update 'Reached Follow Limit' for {row.username}: {e}"
        )
        return False
