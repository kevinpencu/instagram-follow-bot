import time
from app.airtable.profile_repository import AirTableProfileRepository
from app.airtable.enums.profile_status import AirtableProfileStatus
from app.airtable.models.profile import Profile
from app.insta.instagram_selenium import InstagramWrapper
from app.adspower.api_wrapper import adspower
from app.executor import executor, get_executor, delay_executor
from app.logger import get_logger
from app.adspower_selenium import run_selenium
from app.insta.enums.checkpoint import Checkpoint
from app.status_module.profile_status_manager import (
    profile_status_manager,
)
from app.status_module.profile_status_types import BotStatus

attempts_delay_map = {1: 0, 2: 10, 3: 60, 4: 300}


def run_single(profile: Profile, attempt_no: int = 1):
    profile.refresh()

    if profile_status_manager.should_stop(profile.ads_power_id):
        get_logger().info(f"Stopping profile {profile.username}")
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Done
        )
        return

    if attempt_no in attempts_delay_map:
        time.sleep(attempts_delay_map[attempt_no])
    else:
        get_logger().error(
            f"[INSTA-AGENT]: Profile {profile.username} 4th retry, abandoning..."
        )
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Failed
        )
        return

    try:
        get_logger().info(
            f"[INSTA-AGENT]: Initiating Profile {profile.username}"
        )
        profile_status_manager.init_profile(
            profile.username, profile.ads_power_id, BotStatus.Pending
        )

        get_logger().info(
            f"[INSTA-AGENT]: Fetching targets for profile {profile.username}..."
        )
        usernames = profile.download_targets()

        # ERROR-CODE: No Usernames Found
        if len(usernames) <= 0:
            get_logger().error(
                f"[INSTA-AGENT]: No targets found for profile {profile.username}, abandoning..."
            )
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.NoTargets
            )
            return

        get_logger().info(
            f"[INSTA-AGENT]: Fetched {len(usernames)} targets for profile {profile.username}..."
        )

        get_logger().info(
            f"[INSTA-AGENT]: Starting {profile.ads_power_id} AdsPower Session for Profile {profile.username}..."
        )
        start_profile_response = adspower.start_profile(
            profile.ads_power_id
        )

        # ERROR-CODE: Profile Start Failed
        if start_profile_response is None:
            get_logger().error(
                f"[INSTA-AGENT]: Profile {profile.username} start failed, abandoning..."
            )
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.AdsPowerStartFailed
            )
            delay_executor.submit(run_single, profile, attempt_no + 1)
            return

        time.sleep(3)

        get_logger().info(
            f"[INSTA-AGENT]: Profile {profile.username} AdsPower started"
        )

        try:
            selenium_instance = run_selenium(start_profile_response)
        except Exception as e:
            get_logger().error(
                f"[INSTA-AGENT]: Failed to create selenium instance for profile {profile.username}: {str(e)}"
            )
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.SeleniumFailed
            )
            return

        get_logger().info(
            f"[INSTA-AGENT]: Profile {profile.username} starting for {len(usernames)} total usernames"
        )

        profile_status_manager.set_total(
            profile.ads_power_id, len(usernames)
        )
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Running
        )

        processed_usernames = profile.download_processed_targets()
        for username in usernames:
            if profile_status_manager.should_stop(profile.ads_power_id):
                get_logger().info(f"Stopping profile {profile.username}")
                break

            if username in processed_usernames:
                get_logger().info("Skipping already processed username!")
                profile_status_manager.increment_already_followed(
                    profile.ads_power_id
                )
                continue

            result = InstagramWrapper(selenium_instance).follow_action(
                username
            )
            if result == Checkpoint.AlreadyFollowedOrRequested:
                get_logger().info(
                    "AlreadyFollowed! Updating processed targets..."
                )
                profile_status_manager.increment_already_followed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == Checkpoint.PageFollowedOrRequested:
                get_logger().info(
                    "FollowedOrRequested! Updating processed targets..."
                )
                profile_status_manager.increment_total_followed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == Checkpoint.PageUnavailable:
                get_logger().info("AccountLoggedOut!")
                profile_status_manager.increment_total_follow_failed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == Checkpoint.FailedToFollow:
                get_logger().info("FailedToFollow!")
                profile_status_manager.increment_total_follow_failed(
                    profile.ads_power_id
                )
                continue

            if result == Checkpoint.AccountSuspended:
                get_logger().info("AccountIsSuspended!")
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.AccountIsSuspended
                )
                break

            if result == Checkpoint.AccountBanned:
                get_logger().info("AccountBanned!")
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.Banned
                )

                # Update Airtable status to "Banned"
                profile.set_status(AirtableProfileStatus.Banned)
                break

            if result == Checkpoint.FollowBlocked:
                get_logger().info("FollowBlocked!")
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.FollowBlocked
                )
                # Update Airtable with the follow limit reached timestamp
                profile.update_follow_limit_reached()
                break

            if result == Checkpoint.AccountLoggedOut:
                get_logger().info("AccountLoggedOut!")
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.AccountLoggedOut
                )
                # Update Airtable status to "Logged Out"
                profile.set_status(AirtableProfileStatus.LoggedOut)
                break

            if result == Checkpoint.SomethingWentWrongCheckpoint:
                get_logger().info("SomethingWentWrongCheckpoint!")
                profile_status_manager.set_status(
                    profile.ads_power_id,
                    BotStatus.SomethingWentWrong,
                )

                # Update Airtable status to "SomethingWentWrongCheckpoint"
                profile.set_status(
                    AirtableProfileStatus.SomethingWentWrongCheckpoint
                )
                break

            if result == Checkpoint.AccountCompromised:
                get_logger().info(
                    "YourAccountWasCompromised/ChangePassword Checkpoint!"
                )
                profile_status_manager.set_status(
                    profile.ads_power_id,
                    BotStatus.AccountCompromised,
                )

                # Update Airtable status to "ChangePasswordCheckpoint"
                profile.set_status(
                    AirtableProfileStatus.ChangePasswordCheckpoint
                )
                break

            if result == Checkpoint.BadProxy:
                get_logger().info("Bad Proxy 429!")
                profile_status_manager.set_status(
                    profile.ads_power_id,
                    BotStatus.BadProxy,
                )

                # Update Airtable status to "BadProxy"
                profile.set_status(AirtableProfileStatus.BadProxy)
                break

        profile.update_processed_targets(processed_usernames)
        current_profile_stats = profile_status_manager.get_profile_stats(
            profile.ads_power_id
        )
        if (
            current_profile_stats is not None
            and current_profile_stats.is_ok()
        ):
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.Done
            )
            get_logger().info(
                f"[INSTA-AGENT]: Profile {profile.username} completed successfully"
            )

    except Exception as e:
        get_logger().error(
            f"[INSTA-AGENT]: Run single failed for profile {profile.username}. Printing exception and shutting down: {str(e)}."
        )
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Failed
        )
        delay_executor.submit(run_single, profile, attempt_no + 1)
    finally:
        get_logger().info(
            f"[INSTA-AGENT]: Run ended for profile {profile.username}. Updating remote tables and shutting down profile"
        )
        profile.update_processed_targets(processed_usernames)

        try:
            get_logger().info(
                f"[INSTA-AGENT]: Quitting Selenium Instance for username {profile.username}..."
            )
            selenium_instance.quit()
        except Exception as e:
            get_logger().error(
                f"[INSTA-AGENT]: Failed to quit selenium for profile {profile.username}: {str(e)}"
            )

        try:
            get_logger().info(
                f"[INSTA-AGENT]: Stopping AdsPower profile {profile.username}..."
            )
            adspower.stop_profile(profile.ads_power_id)
        except Exception as e:
            get_logger().error(
                f"[INSTA-AGENT]: Failed to stop AdsPower profile {profile.username}: {str(e)}"
            )


def do_start_profiles(profiles: list[Profile], max_workers=4):
    for profile in profiles:
        profile_status_manager.schedule_profile(profile.ads_power_id)

    profile_executor = get_executor(max_workers)
    for profile in profiles:
        profile_executor.submit(run_single, profile)
        time.sleep(1)


def do_start_all(max_workers: int = 4):
    profiles = AirTableProfileRepository().get_profiles()
    do_start_profiles(profiles, max_workers)


def do_start_selected(ads_power_ids: list[str], max_workers: int = 4):
    all_profiles = AirTableProfileRepository().get_profiles()
    selected_profiles = [
        profile
        for profile in all_profiles
        if profile.ads_power_id in ads_power_ids
    ]

    if len(selected_profiles) == 0:
        get_logger().warning(
            f"[INSTA-AGENT]: No profiles found for provided AdsPower IDs: {ads_power_ids}"
        )
        return

    get_logger().info(
        f"[INSTA-AGENT]: Starting automation for {len(selected_profiles)} selected profiles"
    )
    do_start_profiles(selected_profiles, max_workers)


def agent_start_all(max_workers=4):
    executor.submit(do_start_all, max_workers)


def agent_start_selected(ads_power_ids: list, max_workers=4):
    executor.submit(do_start_selected, ads_power_ids, max_workers)


def agent_stop():
    profile_status_manager.stop_all()
