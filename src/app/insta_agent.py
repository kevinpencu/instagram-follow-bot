from app.airtable.helper import (
    get_profiles_mapped,
    fetch_and_parse_usernames,
)
from flask import Flask, request, jsonify
from app.adspower.api_wrapper import adspower
from concurrent.futures import ThreadPoolExecutor
from app.app_status_info import app_status_info
from app.executor import executor
from app.logger import get_logger

def run_single(id: str):
    start_profile_response = adspower.start_profile(id)
    if start_profile_response is None:
        get_logger(__name__).error(f"[INSTA-AGENT]: Profile {id} start failed")


def do_start_all():
    profiles = get_profiles_mapped()
    for profile in profiles:
        executor.submit(run_single, profile.ads_power_id)


def agent_start_all():
    executor.submit(do_start_all)


def agent_start_selected(ids: list):
    pass
