from dataclasses import dataclass
from enum import Enum
import threading


class BotStatus(Enum):
    Pending = "scheduled"
    Running = "running"
    Stopping = "stopping"
    Failed = "failed"
    SeleniumFailed = "seleniumFailed"
    AdsPowerStartFailed = "adsPowerFailed"
    AccountLoggedOut = "accountLoggedOut"
    AccountIsSuspended = "accountSuspended"
    FollowBlocked = "followblocked"
    NoTargets = "notargets"
    Done = "done"
    Banned = "banned"
    SomethingWentWrong = "somethingwentwrong"
    AccountCompromised = "accountcompromised"
    BadProxy = "badproxy"


@dataclass
class ActiveProfileStats:
    ads_power_id: str
    username: str
    bot_status: str
    total_accounts: int
    total_followed: int
    total_follow_failed: int
    total_already_followed: int


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

    def _get_profile_unlocked(
        self, ads_power_id: str
    ) -> ActiveProfileStats:
        """Internal method to get profile without acquiring lock - caller must hold lock"""
        stat = self._data.active_profiles.get(ads_power_id)
        if stat is None:
            return None
        return stat

    def init_profile(
        self, username: str, ads_power_id: str, status: BotStatus
    ) -> ActiveProfileStats:
        with self._lock:
            self._data.active_profiles[ads_power_id] = ActiveProfileStats(
                ads_power_id, username, status.value, 0, 0, 0, 0
            )

    def set_status(self, ads_power_id: str, status: BotStatus):
        with self._lock:
            self._data.active_profiles[ads_power_id].bot_status = (
                status.value
            )

    def set_total(self, ads_power_id: str, total: int):
        with self._lock:
            profile = self._get_profile_unlocked(ads_power_id)
            if profile is None:
                return
            profile.total_accounts = total

    def increment_total_followed(self, ads_power_id: str):
        with self._lock:
            profile = self._get_profile_unlocked(ads_power_id)
            if profile is None:
                return
            profile.total_followed = profile.total_followed + 1

    def increment_total_follow_failed(self, ads_power_id: str):
        with self._lock:
            profile = self._get_profile_unlocked(ads_power_id)
            if profile is None:
                return
            profile.total_follow_failed = profile.total_follow_failed + 1

    def increment_already_followed(self, ads_power_id: str):
        with self._lock:
            profile = self._get_profile_unlocked(ads_power_id)
            if profile is None:
                return
            profile.total_already_followed = (
                profile.total_already_followed + 1
            )

    def schedule(self, ads_power_id: str):
        with self._lock:
            self._data.scheduled_ads_power_ids.append(ads_power_id)

    def unschedule(self, ads_power_id: str):
        with self._lock:
            if ads_power_id in self._data.scheduled_ads_power_ids:
                self._data.scheduled_ads_power_ids.remove(ads_power_id)

    def get_all(self):
        with self._lock:
            return {
                "activeProfiles": self._data.active_profiles,
                "scheduled": self._data.scheduled_ads_power_ids,
            }

    def run_stop_action(self):
        with self._lock:
            for ads_power_id in self._data.active_profiles.keys():
                self._data.active_profiles[ads_power_id].bot_status = (
                    BotStatus.Stopping.value
                )

            for (
                scheduled_ads_power_id
            ) in self._data.scheduled_ads_power_ids:
                if scheduled_ads_power_id in self._data.active_profiles:
                    pass

                self._data.active_profiles[scheduled_ads_power_id] = (
                    ActiveProfileStats(
                        scheduled_ads_power_id,
                        "Stopped",
                        BotStatus.Stopping.value,
                        0,
                        0,
                        0,
                        0,
                    )
                )


app_status_info = AppStatusInfo()
