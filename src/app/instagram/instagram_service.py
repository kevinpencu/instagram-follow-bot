from app.airtable.models.profile import Profile
from app.core.executor import get_executor, delay_executor, executor
import traceback
import time
import random
from datetime import datetime, timezone
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
    FOLLOW_LIMIT_MIN,
    FOLLOW_LIMIT_MAX,
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
        self,
        profiles: list[Profile],
        max_workers: int = DEFAULT_WORKERS,
        accept_requests: bool = False,
        unfollow_users: bool = False,
    ):
        for profile in profiles:
            profile_status_manager.schedule_profile(profile.ads_power_id)

        profile_executor = get_executor(max_workers)

        for profile in profiles:
            get_logger().info(f"Starting profile: {profile.username}")
            profile_executor.submit(
                self.run_single, profile, 1, accept_requests, unfollow_users
            )
            time.sleep(PROFILE_START_DELAY)

    def start_all(
        self,
        max_workers: int = DEFAULT_WORKERS,
        accept_requests: bool = False,
        unfollow_users: bool = False,
    ):
        executor.submit(
            self.do_start_selected,
            AirTableProfileRepository.get_profiles(),
            max_workers,
            accept_requests,
            unfollow_users,
        )

    def start_selected(
        self,
        ads_power_ids: list[str],
        max_workers: int = DEFAULT_WORKERS,
        accept_requests: bool = False,
        unfollow_users: bool = False,
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
            self.do_start_selected,
            selected_profiles,
            max_workers,
            accept_requests,
            unfollow_users,
        )

    def do_start_selected(
        self,
        selected_profiles: list[Profile],
        max_workers: int = DEFAULT_WORKERS,
        accept_requests: bool = False,
        unfollow_users: bool = False,
    ):
        self.start_profiles(
            selected_profiles, max_workers, accept_requests, unfollow_users
        )

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
        self,
        profile: Profile,
        attempt_no: int = 1,
        accept_requests: bool = False,
        unfollow_users: bool = False,
    ) -> webdriver.Chrome:
        profile.refresh()
        profile_status_manager.init_profile(profile)
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Preparing
        )

        usernames = profile.download_targets()
        if len(usernames) <= 0:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.NoTargets
            )
            # Mark in Airtable that new targets are needed
            profile.update_needs_new_targets(True)
            return None

        get_logger().info(
            f"Starting AdsPower For profile: {profile.username}"
        )
        adspower_response = adspower.start_profile(profile.ads_power_id)
        if (
            adspower_response is None
            and self.on_retry(profile, attempt_no + 1, accept_requests, unfollow_users)
            is True
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
            and self.on_retry(profile, attempt_no + 1, accept_requests, unfollow_users)
            is True
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

        # Update last run follows count in AirTable
        get_logger().info(
            f"Updating AirTable with {stats.total_followed} follows for profile {profile.username}"
        )
        profile.update_last_run_follows(stats.total_followed)

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

    def on_retry(
        self,
        profile: Profile,
        attempt_no: int,
        accept_requests: bool = False,
        unfollow_users: bool = False,
    ) -> bool:
        get_logger().error(
            f"Scheduling retry for profile {profile.username}"
        )

        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Retrying
        )

        if delay_for_attempt(attempt_no) is False:
            return False

        delay_executor.submit(
            self.run_single, profile, attempt_no, accept_requests, unfollow_users
        )

        return True

    def run_single(
        self,
        profile: Profile,
        attempt_no: int = 1,
        accept_requests: bool = False,
        unfollow_users: bool = False
    ):
        get_logger().info(f"Running Single: {profile.username}")

        # Ask user for follow mode preference
        print(f"\n{'='*60}")
        print(f"Starting profile: {profile.username}")
        print(f"{'='*60}")
        print("\nChoose follow mode:")
        print("1. Capped (40-45 follows per session)")
        print("2. Uncapped (follow until blocked or suspended)")
        print(f"{'='*60}")

        while True:
            try:
                choice = input("\nEnter your choice (1 or 2): ").strip()
                if choice == "1":
                    # Capped mode - use random limit
                    follow_limit = random.randint(FOLLOW_LIMIT_MIN, FOLLOW_LIMIT_MAX)
                    get_logger().info(f"Follow limit for this session: {follow_limit} (CAPPED MODE)")
                    print(f"\n✓ Capped mode selected. Follow limit: {follow_limit}")
                    break
                elif choice == "2":
                    # Uncapped mode - set very high limit
                    follow_limit = 999999
                    get_logger().info(f"UNCAPPED MODE - Will follow until blocked or suspended")
                    print(f"\n✓ Uncapped mode selected. Will follow until blocked or suspended.")
                    break
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            except (EOFError, KeyboardInterrupt):
                # Default to capped mode if interrupted
                follow_limit = random.randint(FOLLOW_LIMIT_MIN, FOLLOW_LIMIT_MAX)
                get_logger().info(f"Using default capped mode. Follow limit: {follow_limit}")
                print(f"\n✓ Using default capped mode. Follow limit: {follow_limit}")
                break

        print(f"{'='*60}\n")

        # Check if profile is currently follow blocked
        if profile.reached_follow_limit_date:
            try:
                follow_limit_date = datetime.fromisoformat(
                    profile.reached_follow_limit_date.replace('Z', '+00:00')
                )
                current_time = datetime.now(timezone.utc)
                get_logger().info(f"Limit: {follow_limit_date}")
                get_logger().info(f"Current: {current_time}")

                if follow_limit_date > current_time:
                    get_logger().info(
                        f"Profile {profile.username} is follow blocked until {follow_limit_date}, skipping..."
                    )
                    profile_status_manager.init_profile(profile)
                    profile_status_manager.set_status(
                        profile.ads_power_id, BotStatus.FollowBlocked
                    )
                    return
            except (ValueError, TypeError) as e:
                get_logger().warning(
                    f"Invalid reached_follow_limit_date format for {profile.username}: {profile.reached_follow_limit_date}"
                )

        selenium_instance = None
        try:
            selenium_instance = self.prepare_profile(
                profile, attempt_no, accept_requests, unfollow_users
            )

            if selenium_instance is None:
                get_logger().error(
                    f"Preparation for {profile.username} failed."
                )
                return

            targets = profile.download_targets()
            private_targets = profile.download_private_targets()
            processed_targets = profile.download_processed_targets()
            follows_us = profile.download_followsus_targets()
            logged_in = False
            session_follow_count = 0
            using_private_targets = False

            insta_wrapper = InstagramWrapper(selenium_instance)

            if accept_requests:
                get_logger().info(
                    "Accepting Follow Requests Before Following..."
                )
                accepted_users = insta_wrapper.accept_follow_requests()

                # Logged Out
                if accepted_users is None:
                    self.on_handle_status(
                        Checkpoint.AccountLoggedOut,
                        profile,
                        selenium_instance,
                        processed_targets,
                        "",
                    )
                    return

                if len(accepted_users) > 0:
                    follows_us = follows_us + accepted_users
                    profile.update_followsus_targets(follows_us)
                    profile_status_manager.set_total_accepted_accounts(
                        profile.ads_power_id, len(accepted_users)
                    )

            if unfollow_users:
                targets_to_unfollow = []
                follows_us = profile.download_followsus_targets()
                we_follow = profile.download_processed_targets()

                for x in we_follow:
                    if x not in follows_us:
                        targets_to_unfollow.append(x)

                get_logger().info(f"[INSTAGRAMSERVICE]: Unfollowing {len(targets_to_unfollow)} users")
                while len(targets_to_unfollow) > 0 and not profile_status_manager.should_stop(profile.ads_power_id):
                    insta_wrapper.unfollow_user(targets_to_unfollow[0])
                    targets_to_unfollow.remove(targets_to_unfollow[0])


            # Create combined target list: first public (targets), then private (private_targets)
            current_targets = targets.copy()

            while len(current_targets) > 0:
                username = current_targets.pop(0)
                # Check if stop action was initiated
                if profile_status_manager.should_stop(
                    profile.ads_power_id
                ):
                    break

                # Check if follow limit reached
                if session_follow_count >= follow_limit:
                    get_logger().info(
                        f"Profile {profile.username} reached follow limit ({follow_limit}), shutting down..."
                    )
                    self.shutdown_profile(
                        profile,
                        selenium_instance,
                        processed_targets,
                        BotStatus.FollowLimitReached,
                    )
                    return

                # Check if target is already processed
                if username in processed_targets:
                    profile_status_manager.increment_already_followed(
                        profile.ads_power_id
                    )
                    continue

                try:
                    # Run follow action
                    cp = insta_wrapper.follow_action(username)
                    res = self.on_handle_status(
                        cp,
                        profile,
                        selenium_instance,
                        processed_targets,
                        username,
                    )

                    # This means that the profile has been shut down
                    if res is False:
                        return

                    # Check if we need to switch to private targets
                    if res == "switch_to_private" and not using_private_targets:
                        get_logger().info(
                            f"Profile {profile.username} is public follow blocked, switching to private targets..."
                        )
                        using_private_targets = True
                        # Clear current targets and replace with only private targets (excluding already processed)
                        current_targets.clear()
                        for private_target in private_targets:
                            if private_target not in processed_targets:
                                current_targets.append(private_target)
                        get_logger().info(
                            f"Switched to {len(current_targets)} private targets"
                        )
                        continue

                    # Increment session follow count for successful follows
                    if cp in [Checkpoint.PageFollowed, Checkpoint.PageRequested, Checkpoint.PageFollowedOrRequested]:
                        session_follow_count += 1
                        get_logger().info(
                            f"Session follow count: {session_follow_count}/{follow_limit}"
                        )

                    if not logged_in:
                        logged_in = True
                        profile.set_status(AirtableProfileStatus.LoggedIn)

                except Exception as e:
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"
                    get_logger().error(
                        f"User: {profile.username}, Target: {username} Follow Action Failed: {error_msg}. Going to next..."
                    )

            # Check if we ran out of targets (completed the list)
            if len(current_targets) == 0 and not profile_status_manager.should_stop(profile.ads_power_id):
                get_logger().info(f"Profile {profile.username} exhausted all available targets")
                # Mark in Airtable that new targets are needed
                profile.update_needs_new_targets(True)

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
