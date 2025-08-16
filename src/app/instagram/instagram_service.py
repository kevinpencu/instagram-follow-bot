from app.airtable.models.profile import Profile
from app.core.executor import get_executor, delay_executor, executor
import traceback
import time
from app.airtable.enums.profile_status import AirtableProfileStatus
from selenium import webdriver
from app.instagram.instagram_wrapper import InstagramWrapper
from app.status.profile_status_types import BotStatus
from app.instagram.enums.checkpoint import Checkpoint
from app.selenium_utils.adspower_selenium import run_selenium
from app.status.profile_status_manager import (
    profile_status_manager,
)
from app.adspower.api_wrapper import adspower
from app.core.logger import get_logger
from app.airtable.profile_repository import AirTableProfileRepository
from app.instagram.utils import delay_for_attempt
from app.core.constants import (
    DEFAULT_WORKERS,
    SELENIUM_STARTUP_DELAY,
    PROFILE_START_DELAY,
    MAX_SHUTDOWN_ATTEMPTS,
    SHUTDOWN_RETRY_DELAY,
)
from app.instagram.handlers.checkpoint_handlers import (
    create_handler_registry,
    HandlerContext,
)


class InstagramService:
    def __init__(self):
        self._handler_registry = create_handler_registry(
            self.shutdown_profile, profile_status_manager
        )

    def start_profiles(
        self, profiles: list[Profile], max_workers: int = DEFAULT_WORKERS, accept_requests: bool = False
    ):
        for profile in profiles:
            profile_status_manager.schedule_profile(profile.ads_power_id)

        profile_executor = get_executor(max_workers)

        for profile in profiles:
            get_logger().info(f"Starting profile: {profile.username}")
            profile_executor.submit(self.run_single, profile, 1, accept_requests)
            time.sleep(PROFILE_START_DELAY)

    def start_all(self, max_workers: int = DEFAULT_WORKERS, accept_requests: bool = False):
        executor.submit(
            self.do_start_selected,
            AirTableProfileRepository.get_profiles(),
            max_workers,
            accept_requests,
        )

    def start_selected(
            self, ads_power_ids: list[str], max_workers: int = DEFAULT_WORKERS, accept_requests: bool = False
    ):
        all_profiles = AirTableProfileRepository.get_profiles()
        selected_profiles = [
            profile
            for profile in all_profiles
            if profile.ads_power_id in ads_power_ids
        ]

        if len(selected_profiles) == 0:
            return

        executor.submit(
            self.do_start_selected, selected_profiles, max_workers, accept_requests
        )

    def do_start_selected(
        self,
        selected_profiles: list[Profile],
        max_workers: int = DEFAULT_WORKERS,
        accept_requests: bool = False,
    ):
        self.start_profiles(selected_profiles, max_workers, accept_requests)

    def stop_all(self):
        profile_status_manager.stop_all()
        pass

    def on_handle_status(
        self,
        cp: Checkpoint,
        profile: Profile,
        driver: webdriver.Chrome,
        processed_targets: list[str],
        target: str,
    ):
        get_logger().info(f"Processing {cp} checkpoint")
        if cp not in self._handler_registry:
            return True

        return self._handler_registry[cp].handle(
            HandlerContext(profile, driver, processed_targets, target)
        )

    def prepare_profile(
        self, profile: Profile, attempt_no: int = 1, accept_requests: bool = False
    ) -> webdriver.Chrome:
        profile.refresh()
        profile_status_manager.init_profile(profile)
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Preparing
        )

        get_logger().info(
            f"Running delay for profile: {profile.username}"
        )

        if delay_for_attempt(attempt_no) is False:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.MaxRetries
            )
            return None

        usernames = profile.download_targets()
        if len(usernames) <= 0:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.NoTargets
            )
            return None

        get_logger().info(
            f"Starting AdsPower For profile: {profile.username}"
        )
        adspower_response = adspower.start_profile(profile.ads_power_id)
        if (
            adspower_response is None
            and self.on_retry(profile, attempt_no + 1, accept_requests) is True
        ):
            return None

        if adspower_response is None:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.AdsPowerStartFailed
            )
            # Maybe run shutdown
            return None

        get_logger().info(
            f"Waiting before starting selenium for profile: {profile.username}"
        )
        time.sleep(SELENIUM_STARTUP_DELAY)

        get_logger().info(
            f"Starting Selenium For profile: {profile.username}"
        )
        selenium_instance = run_selenium(adspower_response)
        if (
            selenium_instance is None
            and self.on_retry(profile, attempt_no + 1, accept_requests) is True
        ):
            return None

        if selenium_instance is None:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.SeleniumFailed
            )
            try:
                # Shutdown adspower profile
                get_logger().error(
                    f"Shutting down AdsPower Profile for Failed Selenium {profile.username}"
                )
                adspower.stop_profile(profile.ads_power_id)
            except Exception as e:
                get_logger().error(
                    f"Failed to shutdown AdsPower Profile for Failed Selenium Start {profile.username}"
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
        get_logger().info(f"Shutting down profile {profile.username}...")
        if shutdown_attempt_no >= MAX_SHUTDOWN_ATTEMPTS:
            get_logger().info(
                f"Aborting shutdown for down profile {profile.username}..."
            )
            return

        if shutdown_attempt_no == 0:
            profile.update_processed_targets(processed_targets)

        stats = profile_status_manager.get_profile_stats(
            profile.ads_power_id
        )
        if stats is None:
            get_logger().info(
                f"Shutdown for profile {profile.username}... Failed. No Status Present"
            )
            return

        profile_status_manager.set_status(profile.ads_power_id, status)

        try:
            if driver is not None:
                get_logger().info(
                    f"Shutting down selenium for profile {profile.username}"
                )
                driver.quit()
            get_logger().info(
                f"Shutting down AdsPower Profile for profile {profile.username}"
            )
            adspower.stop_profile(profile.ads_power_id)
        except Exception as e:
            get_logger().error(
                f"Shutdown for profile {profile.ads_power_id} failed, sleeping and executing retry no: [{shutdown_attempt_no + 1}]...\n{str(e)}"
            )
            time.sleep(SHUTDOWN_RETRY_DELAY)
            self.shutdown_profile(
                profile,
                driver,
                processed_targets,
                status,
                shutdown_attempt_no + 1,
            )

    def on_retry(self, profile: Profile, attempt_no: int, accept_requests: bool = False) -> bool:
        if delay_for_attempt(attempt_no) is False:
            return False

        get_logger().error(
            f"Scheduling retry for profile {profile.username}"
        )

        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Retrying
        )
        delay_executor.submit(self.run_single, profile, attempt_no, accept_requests)

        return True

    def run_single(self, profile: Profile, attempt_no: int = 1, accept_requests: bool = False):
        get_logger().info(f"Running Single: {profile.username}")
        selenium_instance = None
        try:
            selenium_instance = self.prepare_profile(profile, attempt_no, accept_requests)

            if selenium_instance is None:
                get_logger().error(
                    f"Preparation for {profile.username} failed."
                )
                return

            targets = profile.download_targets()
            processed_targets = profile.download_processed_targets()
            follows_us = profile.download_followsus_targets()
            logged_in = False

            insta_wrapper = InstagramWrapper(selenium_instance)
            
            if accept_requests:
                get_logger().info(
                    "Accepting Follow Requests Before Following..."
                )
                accepted_users = insta_wrapper.accept_follow_requests()
                if len(accepted_users) > 0:
                    follows_us = follows_us + accepted_users
                    profile.update_followsus_targets(follows_us)

            for username in targets:
                # Check if stop action was initiated
                if profile_status_manager.should_stop(
                    profile.ads_power_id
                ):
                    break

                # Check if target is already processed
                if username in processed_targets:
                    profile_status_manager.increment_already_followed(
                        profile.ads_power_id
                    )
                    continue

                try:
                    # Run follow action
                    res = self.on_handle_status(
                        insta_wrapper.follow_action(username),
                        profile,
                        selenium_instance,
                        processed_targets,
                        username,
                    )

                    # This means that the profile has been shut down
                    if res is False:
                        return

                    if not logged_in:
                        logged_in = True
                        profile.set_status(AirtableProfileStatus.LoggedIn)

                except Exception as e:
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"
                    get_logger().error(
                        f"User: {profile.username}, Target: {username} Follow Action Failed: {error_msg}. Going to next..."
                    )

            # Shutdown profile
            self.shutdown_profile(
                profile,
                selenium_instance,
                processed_targets,
                BotStatus.Done,
            )
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            get_logger().error(
                f"Operation Failed: {error_msg}. Shutting down profile..."
            )

            # Shutdown profile
            if selenium_instance is not None:
                self.shutdown_profile(
                    profile,
                    selenium_instance,
                    processed_targets,
                    BotStatus.Done,
                )


instagram_service = InstagramService()
