from typing import Dict
from dataclasses import dataclass
from enum import Enum


class BotStatus(str, Enum):
    Pending = "scheduled"
    Preparing = "preparing"
    Running = "running"
    Stopping = "stopping"
    Failed = "failed"
    MaxRetries = "maxRetries"
    SeleniumFailed = "seleniumFailed"
    AdsPowerStartFailed = "adsPowerFailed"
    Retrying = "retrying"
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
    total_accepted_accounts: int

    def is_ok(self):
        return (
            self.bot_status == BotStatus.Running
            or self.bot_status == BotStatus.Stopping
        )


@dataclass
class ProfileStatusContext:
    active_profiles: Dict[str, ActiveProfileStats]
    scheduled_ads_power_ids: list[str]

    def init_profile(
        self, username: str, ads_power_id: str, status: BotStatus
    ):
        if ads_power_id in self.active_profiles:
            del self.active_profiles[ads_power_id]

        self.unschedule(ads_power_id)

        self.active_profiles[ads_power_id] = ActiveProfileStats(
            ads_power_id, username, status, 0, 0, 0, 0, 0
        )

    def get_profile(self, ads_power_id: str) -> ActiveProfileStats:
        return self.active_profiles.get(ads_power_id)

    def set_status(
        self, ads_power_id: str, status: BotStatus
    ) -> ActiveProfileStats:
        prof = self.get_profile(ads_power_id)
        if prof is None:
            return
        prof.bot_status = status

    def set_total(
        self, ads_power_id: str, total: int
    ) -> ActiveProfileStats:
        prof = self.get_profile(ads_power_id)
        if prof is None:
            return
        prof.total_accounts = total

    def increment_total_followed(
        self, ads_power_id: str
    ) -> ActiveProfileStats:
        prof = self.get_profile(ads_power_id)
        if prof is None:
            return
        prof.total_followed = prof.total_followed + 1

    def increment_total_follow_failed(
        self, ads_power_id: str
    ) -> ActiveProfileStats:
        prof = self.get_profile(ads_power_id)
        if prof is None:
            return
        prof.total_follow_failed = prof.total_follow_failed + 1

    def increment_already_followed(
        self, ads_power_id: str
    ) -> ActiveProfileStats:
        prof = self.get_profile(ads_power_id)
        if prof is None:
            return
        prof.total_already_followed = prof.total_already_followed + 1

    def set_total_accepted_accounts(
        self, ads_power_id: str
    ) -> ActiveProfileStats:
        prof = self.get_profile(ads_power_id)
        if prof is None:
            return
        prof.total_accepted_accounts = prof.total_accepted_accounts + 1


    def schedule(self, ads_power_id: str):
        if ads_power_id in self.scheduled_ads_power_ids:
            return
        self.scheduled_ads_power_ids.append(ads_power_id)

    def unschedule(self, ads_power_id: str):
        if ads_power_id not in self.scheduled_ads_power_ids:
            return
        self.scheduled_ads_power_ids.remove(ads_power_id)

    def get_all(self):
        return {
            "activeProfiles": self.active_profiles,
            "scheduled": self.scheduled_ads_power_ids,
        }
