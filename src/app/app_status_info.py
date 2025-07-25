from dataclasses import dataclass
from enum import Enum
import threading


class BotStatus(Enum):
    PENDING = "scheduled"
    RUNNING = "running"
    FAILED = "failed"
    DONE = "done"


@dataclass
class ActiveProfileStats:
    ads_power_id: str
    username: str
    bot_status: BotStatus
    total_accounts: int
    total_followed: int
    total_follow_failed: int
    total_already_followed: int
    total_private_accounts: int


@dataclass
class AppStatusContext:
    active_profiles: dict
    scheduled_ads_power_ids: list[str]


class AppStatusInfo:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = AppStatusContext({}, [])

    def get_profile(self, ads_power_id: str) -> ActiveProfileStats:
        with self._lock:
            stat = self._data.active_profiles.get(ads_power_id)
            if stat is None:
                return None
            return stat

    def init_profile(
        self, username: str, ads_power_id: str, status: BotStatus
    ) -> ActiveProfileStats:
        with self._lock:
            self._data.active_profiles[ads_power_id] = ActiveProfileStats(
                ads_power_id, username, status, 0
            )

    def increment_total_followed(self, ads_power_id: str):
        with self._lock:
            profile = self.get_profile(ads_power_id)
            if profile is None:
                return
            profile.total_followed = profile.total_followed + 1

    def schedule(self, ads_power_id: str):
        self._data.scheduled_ads_power_ids.append(ads_power_id)

    def unschedule(self, ads_power_id: str):
        if ads_power_id in self._data.scheduled_ads_power_ids:
            self._data.scheduled_ads_power_ids.remove(ads_power_id)

    def get_all(self):
        with self._lock:
            return dict(self._data)


app_status_info = AppStatusInfo()
