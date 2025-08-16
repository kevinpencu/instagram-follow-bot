import threading
from app.airtable.models.profile import Profile
from app.status.profile_status_types import (
    ProfileStatusContext,
    ActiveProfileStats,
    BotStatus,
)


def thread_safe(method):
    """Thread-Safe Decorator"""

    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class ProfileStatusManager:
    _lock: threading.Lock = None
    _profile_stats: ProfileStatusContext

    def __init__(self):
        self._lock = threading.Lock()
        self._profile_stats = ProfileStatusContext({}, [])
        pass

    @thread_safe
    def init_profile(self, profile: Profile) -> ActiveProfileStats:
        self._profile_stats.init_profile(
            profile.username, profile.ads_power_id, BotStatus.Pending
        )

    @thread_safe
    def schedule_profile(self, ads_power_id: str):
        self._profile_stats.schedule(ads_power_id)
        pass

    @thread_safe
    def get_profile_stats(self, ads_power_id: str) -> ActiveProfileStats:
        return self._profile_stats.get_profile(ads_power_id)

    @thread_safe
    def set_status(self, ads_power_id: str, status: BotStatus):
        self._profile_stats.set_status(ads_power_id, status)

    @thread_safe
    def set_total(self, ads_power_id: str, total: int):
        self._profile_stats.set_total(ads_power_id, total)

    @thread_safe
    def set_total_accepted_accounts(self, ads_power_id: str, total: int):
        self._profile_stats.set_total_accepted_accounts(ads_power_id, total)

    @thread_safe
    def increment_total_followed(self, ads_power_id: str):
        self._profile_stats.increment_total_followed(ads_power_id)

    @thread_safe
    def increment_already_followed(self, ads_power_id: str):
        self._profile_stats.increment_already_followed(ads_power_id)

    @thread_safe
    def increment_total_follow_failed(self, ads_power_id: str):
        self._profile_stats.increment_total_follow_failed(ads_power_id)

    @thread_safe
    def get_route_data(self):
        return self._profile_stats.get_all()

    @thread_safe
    def stop_all(self):
        for ads_power_id in self._profile_stats.active_profiles.keys():
            current_status = self._profile_stats.active_profiles[
                ads_power_id
            ].bot_status
            if (
                current_status is BotStatus.Stopping
                or current_status is BotStatus.Failed
                or current_status is BotStatus.Done
            ):
                continue

            self._profile_stats.set_status(
                ads_power_id, BotStatus.Stopping
            )

        for ads_power_id in self._profile_stats.scheduled_ads_power_ids:
            self._profile_stats.init_profile(
                "Stopped", ads_power_id, BotStatus.Stopping
            )

    @thread_safe
    def should_stop(self, ads_power_id: str):
        prof = self._profile_stats.get_profile(ads_power_id)
        if prof is None:
            return False
        return prof.bot_status == BotStatus.Stopping


profile_status_manager = ProfileStatusManager()
