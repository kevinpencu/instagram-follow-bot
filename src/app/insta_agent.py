import time
from app.airtable.helper import (
    get_profiles_mapped,
    fetch_and_parse_usernames,
    refresh_profile,
    fetch_and_parse_processed_targets,
    update_processed_targets,
    update_status,
    update_follow_limit_reached,
)
from app.airtable.models import Profile
from flask import Flask, request, jsonify
from app.adspower.api_wrapper import adspower
from concurrent.futures import ThreadPoolExecutor
from app.app_status_info import app_status_info, BotStatus
from app.executor import executor, get_executor, delay_executor
from app.logger import get_logger
from app.adspower_selenium import run_selenium
from app.automation.instagram_selenium import (
    run_follow_action,
    OperationState,
)
from app.airtable.enum_vals import AirtableProfileStatus

attempts_delay_map = {1: 0, 2: 10, 3: 60, 4: 300}


def should_stop_profile(profile: Profile) -> bool:
    current_profile = app_status_info.get_profile(profile.ads_power_id)
    return (
        current_profile is not None
        and current_profile.bot_status == BotStatus.Stopping.value
    )


def run_single(profile: Profile, attempt_no: int = 1):
    profile = refresh_profile(profile)
    if should_stop_profile(profile):
        get_logger().info(f"Stopping profile {profile.username}")
        app_status_info.set_status(profile.ads_power_id, BotStatus.Done)
        return

    if attempt_no in attempts_delay_map:
        time.sleep(attempts_delay_map[attempt_no])
    else:
        get_logger().error(
            f"[INSTA-AGENT]: Profile {profile.username} 4th retry, abandoning..."
        )
        app_status_info.set_status(profile.ads_power_id, BotStatus.Failed)
        return

    try:
        get_logger().info(
            f"[INSTA-AGENT]: Initiating Profile {profile.username}"
        )

        app_status_info.init_profile(
            profile.username, profile.ads_power_id, BotStatus.Pending
        )
        app_status_info.unschedule(profile.ads_power_id)

        get_logger().info(
            f"[INSTA-AGENT]: Fetching targets for profile {profile.username}..."
        )
        usernames = fetch_and_parse_usernames(profile)

        # ERROR-CODE: No Usernames Found
        if len(usernames) <= 0:
            get_logger().error(
                f"[INSTA-AGENT]: No targets found for profile {profile.username}, abandoning..."
            )
            app_status_info.set_status(
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
            app_status_info.set_status(
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
            app_status_info.set_status(
                profile.ads_power_id, BotStatus.SeleniumFailed
            )
            return

        get_logger().info(
            f"[INSTA-AGENT]: Profile {profile.username} starting for {len(usernames)} total usernames"
        )

        app_status_info.set_total(profile.ads_power_id, len(usernames))
        app_status_info.set_status(
            profile.ads_power_id, BotStatus.Running
        )

        processed_usernames = fetch_and_parse_processed_targets(profile)
        for username in usernames:
            if should_stop_profile(profile):
                get_logger().info(f"Stopping profile {profile.username}")
                break

            if username in processed_usernames:
                get_logger().info("Skipping already processed username!")
                app_status_info.increment_already_followed(
                    profile.ads_power_id
                )
                continue

            result = run_follow_action(selenium_instance, username)
            if result == OperationState.AlreadyFollowed:
                get_logger().info(
                    "AlreadyFollowed! Updating processed targets..."
                )
                app_status_info.increment_already_followed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == OperationState.FollowedOrRequested:
                get_logger().info(
                    "FollowedOrRequested! Updating processed targets..."
                )
                app_status_info.increment_total_followed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == OperationState.PageUnavailable:
                get_logger().info("AccountLoggedOut!")
                app_status_info.increment_total_follow_failed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == OperationState.FailedToFollow:
                get_logger().info("FailedToFollow!")
                app_status_info.increment_total_follow_failed(
                    profile.ads_power_id
                )
                continue

            if result == OperationState.AccountIsSuspended:
                get_logger().info("AccountIsSuspended!")
                app_status_info.set_status(
                    profile.ads_power_id, BotStatus.AccountIsSuspended
                )
                break

            if result == OperationState.AccountBanned:
                get_logger().info("AccountBanned!")
                app_status_info.set_status(
                    profile.ads_power_id, BotStatus.Banned
                )

                # Update Airtable status to "Banned"
                update_status(profile, AirtableProfileStatus.Banned.value)
                break

            if result == OperationState.FollowBlocked:
                get_logger().info("FollowBlocked!")
                app_status_info.set_status(
                    profile.ads_power_id, BotStatus.FollowBlocked
                )
                # Update Airtable with the follow limit reached timestamp
                update_follow_limit_reached(profile)
                break

            if result == OperationState.AccountLoggedOut:
                get_logger().info("AccountLoggedOut!")
                app_status_info.set_status(
                    profile.ads_power_id, BotStatus.AccountLoggedOut
                )
                # Update Airtable status to "Logged Out"
                update_status(
                    profile, AirtableProfileStatus.LoggedOut.value
                )
                break

            if result == OperationState.SomethingWentWrongCheckpoint:
                get_logger().info("SomethingWentWrongCheckpoint!")
                app_status_info.set_status(
                    profile.ads_power_id,
                    BotStatus.SomethingWentWrong,
                )

                # Update Airtable status to "SomethingWentWrongCheckpoint"
                update_status(
                    profile,
                    AirtableProfileStatus.SomethingWentWrongCheckpoint.value,
                )
                break

            if result == OperationState.YourAccountWasCompromised:
                get_logger().info(
                    "YourAccountWasCompromised/ChangePassword Checkpoint!"
                )
                app_status_info.set_status(
                    profile.ads_power_id,
                    BotStatus.AccountCompromised,
                )

                # Update Airtable status to "ChangePasswordCheckpoint"
                update_status(
                    profile,
                    AirtableProfileStatus.ChangePasswordCheckpoint.value,
                )
                break

            if result == OperationState.BadProxy:
                get_logger().info("Bad Proxy 429!")
                app_status_info.set_status(
                    profile.ads_power_id,
                    BotStatus.BadProxy,
                )

                # Update Airtable status to "BadProxy"
                update_status(
                    profile,
                    AirtableProfileStatus.BadProxy.value,
                )
                break

        update_processed_targets(profile, processed_usernames)
        current_profile = app_status_info.get_profile(
            profile.ads_power_id
        )
        if current_profile and (
            current_profile.bot_status == BotStatus.Running.value
            or current_profile.bot_status == BotStatus.Stopping.value
        ):
            app_status_info.set_status(
                profile.ads_power_id, BotStatus.Done
            )
            get_logger().info(
                f"[INSTA-AGENT]: Profile {profile.username} completed successfully"
            )

    except Exception as e:
        get_logger().error(
            f"[INSTA-AGENT]: Run single failed for profile {profile.username}. Printing exception and shutting down: {str(e)}."
        )
        app_status_info.set_status(profile.ads_power_id, BotStatus.Failed)
        delay_executor.submit(run_single, profile, attempt_no + 1)
    finally:
        get_logger().error(
            f"[INSTA-AGENT]: Run ended for profile {profile.username}. Updating remote tables and shutting down profile"
        )
        update_processed_targets(profile, processed_usernames)

        try:
            selenium_instance.quit()
        except Exception as e:
            get_logger().error(
                f"[INSTA-AGENT]: Failed to quit selenium for profile {profile.username}: {str(e)}"
            )

        try:
            adspower.stop_profile(profile.ads_power_id)
        except Exception as e:
            get_logger().error(
                f"[INSTA-AGENT]: Failed to stop AdsPower profile {profile.username}: {str(e)}"
            )


def do_start_profiles(profiles, max_workers=4):
    """Common logic to start automation for a list of profiles"""
    for profile in profiles:
        app_status_info.schedule(profile.ads_power_id)

    profile_executor = get_executor(max_workers)
    for profile in profiles:
        profile_executor.submit(run_single, profile)
        time.sleep(1)


def do_start_all(max_workers=4):
    """Start automation for all profiles"""
    profiles = get_profiles_mapped()
    do_start_profiles(profiles, max_workers)


def do_start_selected(ads_power_ids, max_workers=4):
    """Start automation for selected profiles by AdsPower IDs"""
    all_profiles = get_profiles_mapped()
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
    app_status_info.run_stop_action()
