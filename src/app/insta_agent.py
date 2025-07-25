import time
from app.airtable.helper import (
    get_profiles_mapped,
    fetch_and_parse_usernames,
    ProfileDataRow,
)
from flask import Flask, request, jsonify
from app.adspower.api_wrapper import adspower
from concurrent.futures import ThreadPoolExecutor
from app.app_status_info import app_status_info
from app.executor import executor
from app.logger import get_logger
from app.adspower_selenium import run_selenium
from app.automation.instagram_selenium import run_follow_action


def run_single(profile: ProfileDataRow):
    get_logger().info(
        f"[INSTA-AGENT]: Fetching targets for profile {profile.username}..."
    )
    usernames = fetch_and_parse_usernames(profile)

    # ERROR-CODE: No Usernames Found
    if len(usernames) <= 0:
        get_logger().error(
            f"[INSTA-AGENT]: No targets found for profile {profile.username}, abandoning..."
        )
        return

    get_logger().info(
        f"[INSTA-AGENT]: Fetched {len(usernames)} targets for profile {profile.username}..."
    )

    get_logger().info(
        f"[INSTA-AGENT]: Starting {profile.ads_power_id} AdsPower Session for Profile {profile.username}..."
    )
    start_profile_response = adspower.start_profile(profile.ads_power_id)

    # ERROR-CODE: Profile Start Failed
    if start_profile_response is None:
        get_logger().error(
            f"[INSTA-AGENT]: Profile {profile.username} start failed, abandoning..."
        )
        return
    time.sleep(3)
    get_logger().info(
        f"[INSTA-AGENT]: Profile {profile.username} AdsPower started"
    )

    selenium_instance = run_selenium(start_profile_response)

    get_logger().info(
        f"[INSTA-AGENT]: Profile {profile.username} starting for {len(usernames)} total usernames"
    )

    for username in usernames:
        # TODO(HSI): Parse result and adjust app info status
        run_follow_action(selenium_instance, username)


def do_start_all():
    profiles = get_profiles_mapped()
    for profile in profiles:
        get_logger().info(
            f"[INSTA-AGENT]: Initiating Profile {profile.username}"
        )
        # executor.submit(run_single, profile)
        run_single(profile)


def agent_start_all():
    # executor.submit(do_start_all)
    do_start_all()


def agent_start_selected(ids: list):
    pass
