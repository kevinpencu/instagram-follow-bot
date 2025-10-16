from app.airtable.models.profile import (
    Profile,
    TARGETS_FIELD_COLUMN,
    PRIVATE_TARGETS_FIELD_COLUMN,
    ADSPOWER_ID_COLUMN,
    USERNAME_COLUMN,
    PROFILE_NAME_COLUMN,
    ALREADY_FOLLOWED_COLUMN,
    FOLLOWS_US_COLUMN,
    REACHED_FOLLOW_LIMIT,
)
from app.airtable.helper import get_table, config
from app.core.logger import get_logger

ALL_FIELDS = [
    TARGETS_FIELD_COLUMN,
    PRIVATE_TARGETS_FIELD_COLUMN,
    ADSPOWER_ID_COLUMN,
    USERNAME_COLUMN,
    PROFILE_NAME_COLUMN,
    ALREADY_FOLLOWED_COLUMN,
    FOLLOWS_US_COLUMN,
    REACHED_FOLLOW_LIMIT,
]


class AirTableProfileRepository:
    def __init__(self):
        pass

    @staticmethod
    def get_profiles() -> list[Profile]:
        table = get_table()
        all_records = []

        try:
            for batch in table.iterate(
                fields=ALL_FIELDS,
                view=config["viewId"],
                page_size=100,
            ):
                all_records.extend([Profile.from_dict(x) for x in batch])

            get_logger().info(
                f"[AirTableProfileWrapper]: Fetched {len(all_records)} profiles"
            )

            return all_records
        except Exception as e:
            get_logger().error(
                f"Failed to fetch profiles. Requested fields: {ALL_FIELDS}. "
                f"View ID: {config.get('viewId')}. Error: {str(e)}"
            )
            # Try fetching without field restrictions to see all available fields
            get_logger().info("Attempting to fetch without field restrictions...")
            try:
                for batch in table.iterate(
                    view=config["viewId"],
                    page_size=100,
                ):
                    all_records.extend([Profile.from_dict(x) for x in batch])
                    # Log available fields from first record
                    if len(batch) > 0 and len(all_records) == len(batch):
                        available_fields = list(batch[0].get("fields", {}).keys())
                        get_logger().info(f"Available fields in Airtable: {available_fields}")

                get_logger().info(
                    f"[AirTableProfileWrapper]: Successfully fetched {len(all_records)} profiles without field restrictions"
                )
                return all_records
            except Exception as fallback_error:
                get_logger().error(f"Fallback fetch also failed: {str(fallback_error)}")
                raise
