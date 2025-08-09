from app.airtable.models.profile import Profile
from app.executor import executor, get_executor, delay_executor
from app.airtable.enums.profile_status import AirtableProfileStatus
from selenium import webdriver
from app.insta.instagram_selenium import InstagramWrapper
from app.status_module.profile_status_types import BotStatus
from app.insta.enums.checkpoint import Checkpoint
from app.selenium_utils.adspower_selenium import run_selenium
from app.status_module.profile_status_manager import (
    profile_status_manager,
)
from app.adspower.api_wrapper import adspower


class InstagramService:
    def __init__(self):
        self._handlers = {
            Checkpoint.AlreadyFollowedOrRequested: self.already_followed_or_requested_handler,
            Checkpoint.PageFollowedOrRequested: self.followed_or_requested_handler,
            Checkpoint.PageUnavailable: self.page_unavailable_handler,
            Checkpoint.FailedToFollow: self.failed_follow_handler,
            Checkpoint.AccountSuspended: self.account_suspended_handler,
            Checkpoint.AccountBanned: self.account_banned_handler,
            Checkpoint.FollowBlocked: self.follow_blocked_handler,
            Checkpoint.AccountLoggedOut: self.account_logged_out_handler,
            Checkpoint.SomethingWentWrongCheckpoint: self.something_went_wrong_handler,
            Checkpoint.AccountCompromised: self.account_compromised_handler,
            Checkpoint.BadProxy: self.bad_proxy_handler,
        }

    def on_attempt_delay(attempt_no: int = 0):
        attempts_delay_map = {1: 0, 2: 10, 3: 60, 4: 300}
        if attempt_no not in attempts_delay_map:
            return False
        time.sleep(attempts_delay_map[attempt_no])

    def start_all(self, max_workers: int = 4):
        pass

    def start_selected(self, max_workers: int = 4):
        pass

    def stop_all(self, max_workers: int = 4):
        pass

    def already_followed_or_requested_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:

        profile_status_manager.increment_already_followed(
            profile.ads_power_id
        )
        processed_targets.append(target)

        return True

    def followed_or_requested_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        profile_status_manager.increment_total_followed(
            profile.ads_power_id
        )
        processed_targets.append(target)

        return True

    def page_unavailable_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        profile_status_manager.increment_total_follow_failed(
            profile.ads_power_id
        )
        processed_targets.append(target)
        return True

    def failed_follow_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        profile_status_manager.increment_total_follow_failed(
            profile.ads_power_id
        )
        return True

    def account_suspended_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        self.shutdown_profile(
            profile,
            driver,
            processed_targets,
            BotStatus.AccountIsSuspended,
        )
        return False

    def account_banned_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        self.shutdown_profile(
            profile, driver, processed_targets, BotStatus.Banned
        )
        return False

    def follow_blocked_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        profile.update_follow_limit_reached()
        self.shutdown_profile(
            profile, driver, processed_targets, BotStatus.FollowBlocked
        )
        return False

    def account_logged_out_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        self.shutdown_profile(
            profile, driver, processed_targets, BotStatus.AccountLoggedOut
        )
        return False

    def something_went_wrong_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        self.shutdown_profile(
            profile,
            driver,
            processed_targets,
            BotStatus.SomethingWentWrong,
        )
        return Falsee

    def account_compromised_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        self.shutdown_profile(
            profile,
            driver,
            processed_targets,
            BotStatus.AccountCompromised,
        )
        profile.set_status(AirtableProfileStatus.ChangePasswordCheckpoint)

    def bad_proxy_handler(
        self, profile: Profile, processed_targets: list[str], target: str
    ) -> bool:
        self.shutdown_profile(
            profile,
            driver,
            processed_targets,
            BotStatus.BadProxy,
        )
        profile.set_status(AirtableProfileStatus.BadProxy)
        return False

    def on_handle_status(
        self,
        cp: Checkpoint,
        profile: Profile,
        processed_targets: list[str],
        target: str,
    ):
        if cp not in self._handlers:
            return True

        return handlers[cp](profile, processed_targets, target)

    def prepare_profile(
        self, profile: Profile, attempt_no: int = 0
    ) -> webdriver.Chrome:
        if profile_manager.should_stop(profile.ads_power_id):
            profile_manager.set_status(
                profile.ads_power_id, BotStatus.Done
            )
            return None

        if self.on_attempt_delay(attempt_no) is False:
            profile_manager.set_status(
                profile.ads_power_id, BotStatus.Failed
            )
            return None

        profile_status_manager.init_profile(profile)

        usernames = profile.download_targets()
        if len(usernames) <= 0:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.NoTargets
            )
            return None

        adspower_response = adspower.start_profile(profile.ads_power_id)
        if (
            adspower_response is None
            and self.on_retry(profile, attempt_no) is True
        ):
            return None

        if adspower_response is None:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.AdsPowerStartFailed
            )
            return None

        time.sleep(3)

        selenium_instance = run_selenium(start_profile_response)
        if (
            selenium_instance is None
            and self.on_retry(profile, attempt_no) is True
        ):
            return None

        if selenium_instance is None:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.SeleniumFailed
            )
            return None

        profile_status_manager.set_total(
            profile.ads_power_id, len(usernames)
        )
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Running
        )

        return selenium_instance

    def shutdown_profile(
        self,
        profile: Profile,
        driver: webdriver.Chrome,
        processed_targets: list[str],
        status: BotStatus,
        shutdown_attempt_no: int = 0,
    ):
        if shutdown_attempt_no >= 3:
            return

        if shutdown_attempt_no == 0:
            profile.update_processed_targets(processed_targets)

        stats = profile_status_manager.get_profile_stats(
            profile.ads_power_id
        )
        if stats is None:
            return

        if stats.is_ok():
            profile_status_manager.mark_done(profile.ads_power_id)
        else:
            profile_status_manager.set_status(
                profile.ads_power_id, status
            )

        try:
            driver.quit()
            adspower.stop_profile(profile.ads_power_id)
        except Exception as e:
            time.sleep(5)
            self.shutdown_profile(
                profile, driver, processed_targets, status, shutdown_attempt_no + 1
            )

    def on_retry(self, profile: Profile, attempt_no: int) -> bool:
        if attempt_no > 4:
            return False

        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Retrying
        )
        delay_executor.submit(self.run_single, profile, attempt_no)

        return True

    def run_single(self, profile: Profile, attempt_no: int = 0):
        selenium_instance = self.prepare_profile(profile, attempt_no)

        if prepare_profile_response is None:
            return

        targets = profile.download_targets()
        processed_targets = profile.download_processed_targets()

        for username in targets:
            # Check if stop action was initiated
            if profile_status_manager.should_stop(profile.ads_power_id):
                break

            # Check if target is already processed
            profile_status_manager.increment_already_followed(
                profile.ads_power_id
            )

            instagram_wrapper = InstagramWrapper(selenium_instance)
            res = instagram_wrapper.follow_action(username)


instagram_service = InstagramService()
