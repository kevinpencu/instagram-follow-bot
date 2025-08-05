from dataclasses import dataclass
from datetime import datetime, timezone
from app.airtable.helper import (
    get_table,
    parse_urls_from_attachment_field,
    download_and_parse_lines_from_url,
)

DEFAULT_ATTACHMENT_FILE_NAME = "usernames.txt"
TARGETS_FIELD_COLUMN = "Targets"
ADSPOWER_ID_COLUMN = "AdsPower ID"
USERNAME_COLUMN = "Username"
ALREADY_FOLLOWED_COLUMN = "Already Followed"
FOLLOWS_US_COLUMN = "Follows Us"


@dataclass
class Profile:
    airtable_id: str
    ads_power_id: str
    username: str
    target_download_urls: list[str]
    processed_targets_download_urls: list[str]
    followsus_targets_download_urls: list[str]

    @staticmethod
    def from_dict(x: dict):
        return Profile(
            record["id"],
            record["fields"][ADSPOWER_ID_COLUMN],
            record["fields"][USERNAME_COLUMN],
            parse_urls_from_attachment_field(
                record["fields"][TARGETS_FIELD_COLUMN]
            ),
            parse_urls_from_attachment_field(
                record["fields"][ALREADY_FOLLOWED_COLUMN]
            ),
            parse_urls_from_attachment_field(
                record["fields"][FOLLOWS_US_COLUMN]
            ),
        )

    def update_usernames(self, usernames: list[str], field_column: str):
        record = get_table().get(row.airtable_id)

        content = "\n".join(usernames)

        result = get_table().upload_attachment(
            record_id=row.airtable_id,
            field=field_column,
            filename=DEFAULT_ATTACHMENT_FILE_NAME,
            content=content,
            content_type="text/plain",
        )

        updated_record = get_table().get(row.airtable_id)
        processed_files = updated_record.get("fields", {}).get(
            field_column, []
        )

        if len(processed_files) > 1:
            get_table().update(
                row.airtable_id,
                {field_column: [processed_files[-1]]},
            )

    def refresh(self):
        x = get_table().get(self.airtable_id)
        if x is None:
            return

        self.__dict__.update(Profile.from_dict(x))

    def download_targets(self) -> list[str]:
        return download_and_parse_lines_from_url(
            self.target_download_urls
        )

    def download_processed_targets(self) -> list[str]:
        return download_and_parse_lines_from_url(
            self.processed_targets_download_urls
        )

    def download_followsus_targets(self) -> list[str]:
        return download_and_parse_lines_from_url(
            self.followsus_targets_download_urls
        )

    def set_status(self, status: str):
        get_table().update(self.airtable_id, {"Status": [status]})

    def update_follow_limit_reached(self):
        get_table().update(
            self.airtable_id,
            {
                "Reached Follow Limit": datetime.now(
                    timezone.utc
                ).isoformat()
            },
        )
