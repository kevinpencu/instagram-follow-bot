import time
from app.airtable.helper import (
    get_profiles_mapped,
    fetch_and_parse_usernames,
    ProfileDataRow,
)
from flask import Flask, request, jsonify
from app.adspower.api_wrapper import adspower
from concurrent.futures import ThreadPoolExecutor
from app.app_status_info import app_status_info, BotStatus
from app.executor import executor, get_executor
from app.logger import get_logger
from app.adspower_selenium import run_selenium
from app.automation.instagram_selenium import (
    run_follow_action,
    OperationState,
)


def run_single(profile: ProfileDataRow):
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

        # usernames = usernames[:4]

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

        for username in usernames:
            result = run_follow_action(selenium_instance, username)
            if result == OperationState.AlreadyFollowed:
                get_logger().info("AlreadyFollowed!")
                app_status_info.increment_already_followed(
                    profile.ads_power_id
                )
                continue

            if result == OperationState.FollowedOrRequested:
                get_logger().info("FollowedOrRequested!")
                app_status_info.increment_total_followed(
                    profile.ads_power_id
                )
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

            if result == OperationState.FollowBlocked:
                get_logger().info("FollowBlocked!")
                app_status_info.set_status(
                    profile.ads_power_id, BotStatus.FollowBlocked
                )
                break

            if result == OperationState.AccountLoggedOut:
                get_logger().info("AccountLoggedOut!")
                app_status_info.set_status(
                    profile.ads_power_id, BotStatus.AccountLoggedOut
                )
                break

        current_profile = app_status_info.get_profile(
            profile.ads_power_id
        )
        if (
            current_profile
            and current_profile.bot_status == BotStatus.Running.value
        ):
            app_status_info.set_status(
                profile.ads_power_id, BotStatus.Done
            )
            get_logger().info(
                f"[INSTA-AGENT]: Profile {profile.username} completed successfully"
            )

    except Exception as e:
        get_logger().error(
            f"[INSTA-AGENT]: Run single failed for profile {profile.username}: {str(e)}"
        )
        app_status_info.set_status(profile.ads_power_id, BotStatus.Failed)
    finally:
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
