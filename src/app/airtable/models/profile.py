from dataclasses import dataclass
from datetime import datetime, timezone
from app.airtable.helper import (
    get_table,
    map_attachment_field_to_urls,
    download_and_parse_lines_from_url,
)
from app.airtable.enums.profile_status import AirtableProfileStatus

DEFAULT_ATTACHMENT_FILE_NAME = "usernames.txt"
TARGETS_FIELD_COLUMN = "Targets"
ADSPOWER_ID_COLUMN = "AdsPower ID"
USERNAME_COLUMN = "Username"
ALREADY_FOLLOWED_COLUMN = "Already Followed"
FOLLOWS_US_COLUMN = "Follows Us"
REACHED_FOLLOW_LIMIT = "Reached Follow Limit"


@dataclass
class Profile:
    airtable_id: str
    ads_power_id: str
    username: str
    target_download_urls: list[str]
    processed_targets_download_urls: list[str]
    followsus_targets_download_urls: list[str]
    reached_follow_limit_date: str

    @staticmethod
    def from_dict(x: dict):
        return Profile(
            x["id"],
            x["fields"][ADSPOWER_ID_COLUMN],
            x["fields"][USERNAME_COLUMN],
            map_attachment_field_to_urls(
                x["fields"][TARGETS_FIELD_COLUMN]
            ),
            map_attachment_field_to_urls(
                x["fields"].get(ALREADY_FOLLOWED_COLUMN)
            ),
            map_attachment_field_to_urls(
                x["fields"].get(FOLLOWS_US_COLUMN)
            ),
            x["fields"].get(REACHED_FOLLOW_LIMIT),
        )

    def update_usernames(self, usernames: list[str], field_column: str):
        content = "\n".join(usernames)

        get_table().upload_attachment(
            record_id=self.airtable_id,
            field=field_column,
            filename=DEFAULT_ATTACHMENT_FILE_NAME,
            content=content,
            content_type="text/plain",
        )

        updated_record = get_table().get(self.airtable_id)
        processed_files = updated_record.get("fields", {}).get(
            field_column, []
        )

        if len(processed_files) > 1:
            get_table().update(
                self.airtable_id,
                {field_column: [processed_files[-1]]},
            )

    def refresh(self):
        x = get_table().get(self.airtable_id)
        if x is None:
            return

        new_profile = Profile.from_dict(x)

        self.target_download_urls = new_profile.target_download_urls
        self.processed_targets_download_urls = (
            new_profile.processed_targets_download_urls
        )
        self.followsus_targets_download_urls = (
            new_profile.followsus_targets_download_urls
        )
        self.reached_follow_limit_date = (
            new_profile.reached_follow_limit_date
        )

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

    def update_processed_targets(self, usernames: list[str]):
        self.update_usernames(usernames, ALREADY_FOLLOWED_COLUMN)

    def update_followsus_targets(self, usernames: list[str]):
        self.update_usernames(usernames, FOLLOWS_US_COLUMN)

    def set_status(self, status: AirtableProfileStatus):
        get_table().update(self.airtable_id, {"Status": [status]})

    def update_follow_limit_reached(self):
        get_table().update(
            self.airtable_id,
            {
                REACHED_FOLLOW_LIMIT: datetime.now(
                    timezone.utc
                ).isoformat()
            },
        )
