from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from app.airtable.helper import (
    get_table,
    map_attachment_field_to_urls,
    download_and_parse_lines_from_url,
)
from app.airtable.enums.profile_status import AirtableProfileStatus
from app.core.logger import get_logger

DEFAULT_ATTACHMENT_FILE_NAME = "usernames.txt"
TARGETS_FIELD_COLUMN = "Targets"
PRIVATE_TARGETS_FIELD_COLUMN = "Private Targets"
ADSPOWER_ID_COLUMN = "AdsPower ID"
USERNAME_COLUMN = "Username"
PROFILE_NAME_COLUMN = "Profile Name"
ALREADY_FOLLOWED_COLUMN = "Already Followed"
FOLLOWS_US_COLUMN = "Follows Us"
REACHED_FOLLOW_LIMIT = "Reached Follow Limit"
LAST_RUN_FOLLOWS = "Last run follows"
NEEDS_NEW_TARGETS = "Needs new targets"


@dataclass
class Profile:
    airtable_id: str
    ads_power_id: str
    username: str
    profile_name: str
    target_download_urls: list[str]
    private_targets_download_urls: list[str]
    processed_targets_download_urls: list[str]
    followsus_targets_download_urls: list[str]
    reached_follow_limit_date: str
    cached_targets: list[str]
    cached_private_targets: list[str]

    @staticmethod
    def from_dict(x: dict):
        return Profile(
            airtable_id=x["id"],
            ads_power_id=x["fields"][ADSPOWER_ID_COLUMN],
            username=x["fields"][USERNAME_COLUMN],
            profile_name=x["fields"].get(PROFILE_NAME_COLUMN, ""),
            target_download_urls=map_attachment_field_to_urls(
                x["fields"].get(TARGETS_FIELD_COLUMN)
            ),
            private_targets_download_urls=map_attachment_field_to_urls(
                x["fields"].get(PRIVATE_TARGETS_FIELD_COLUMN)
            ),
            processed_targets_download_urls=map_attachment_field_to_urls(
                x["fields"].get(ALREADY_FOLLOWED_COLUMN)
            ),
            followsus_targets_download_urls=map_attachment_field_to_urls(
                x["fields"].get(FOLLOWS_US_COLUMN)
            ),
            reached_follow_limit_date=x["fields"].get(
                REACHED_FOLLOW_LIMIT
            ),
            cached_targets=[],
            cached_private_targets=[],
        )

    def update_usernames(self, usernames: list[str], field_column: str):
        if len(usernames) <= 0:
            usernames = ["mandatory_first_entry"]
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
        self.private_targets_download_urls = new_profile.private_targets_download_urls
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
        get_logger().info(
            f"[PROFILE]: Fetching targets for profile {self.username}"
        )

        if len(self.cached_targets) > 0:
            return self.cached_targets

        self.cached_targets = download_and_parse_lines_from_url(
            self.target_download_urls
        )
        return self.cached_targets

    def download_processed_targets(self) -> list[str]:
        get_logger().info("[PROFILE]: Fetching Already Followed Targets")

        return download_and_parse_lines_from_url(
            self.processed_targets_download_urls
        )

    def download_followsus_targets(self) -> list[str]:
        get_logger().info("[PROFILE]: Fetching Follows Us Targets")

        return download_and_parse_lines_from_url(
            self.followsus_targets_download_urls
        )

    def download_private_targets(self) -> list[str]:
        get_logger().info(
            f"[PROFILE]: Fetching private targets for profile {self.username}"
        )

        if len(self.cached_private_targets) > 0:
            return self.cached_private_targets

        self.cached_private_targets = download_and_parse_lines_from_url(
            self.private_targets_download_urls
        )
        return self.cached_private_targets

    def update_processed_targets(self, usernames: list[str]):
        self.update_usernames(usernames, ALREADY_FOLLOWED_COLUMN)

    def update_followsus_targets(self, usernames: list[str]):
        self.update_usernames(usernames, FOLLOWS_US_COLUMN)

    def set_status(self, status: AirtableProfileStatus):
        get_table().update(self.airtable_id, {"Status": [status]})

    def update_follow_limit_reached(self):
        follow_limit_time = datetime.now(timezone.utc) + timedelta(hours=24)
        get_table().update(
            self.airtable_id,
            {
                REACHED_FOLLOW_LIMIT: follow_limit_time.isoformat()
            },
        )

    def update_last_run_follows(self, follow_count: int):
        get_table().update(
            self.airtable_id,
            {
                LAST_RUN_FOLLOWS: follow_count
            },
        )

    def update_needs_new_targets(self, needs_targets: bool):
        """Update the 'Needs new targets' column in Airtable"""
        value = "Yes" if needs_targets else "No"
        get_logger().info(f"[PROFILE]: Setting 'Needs new targets' to '{value}' for {self.username}")
        get_table().update(
            self.airtable_id,
            {
                NEEDS_NEW_TARGETS: value
            },
        )
