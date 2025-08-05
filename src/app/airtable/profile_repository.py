from app.airtable.models.profile import Profile
from app.airtable.helper import get_table, config
from app.logger import get_logger

TARGETS_FIELD_COLUMN = "Targets"
ADSPOWER_ID_COLUMN = "AdsPower ID"
USERNAME_COLUMN = "Username"
ALREADY_FOLLOWED_COLUMN = "Already Followed"
FOLLOWS_US_COLUMN = "Follows Us"

ALL_FIELDS = [
    TARGETS_FIELD_COLUMN,
    ADSPOWER_ID_COLUMN,
    USERNAME_COLUMN,
    ALREADY_FOLLOWED_COLUMN,
    FOLLOWS_US_COLUMN,
]


class AirTableProfileRepository:
    def __init__(self):
        pass

    @staticmethod
    def get_profiles() -> list[Profile]:
        table = get_table()
        all_records = []

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
