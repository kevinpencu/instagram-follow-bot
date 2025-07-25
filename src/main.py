from app.airtable.helper import (
    get_profiles,
    fetch_and_parse_usernames,
    get_profiles_mapped,
)
from flask import Flask, request, jsonify
from app.adspower.api_wrapper import adspower
from app.app_status_info import app_status_info
from app.executor import executor
from app.insta_agent import agent_start_all, agent_start_selected

app = Flask(__name__)


@app.route("/profiles")
def profiles():
    return get_profiles_mapped()


@app.route("/start-all", methods=["POST"])
def start():
    agent_start_all()
    return {}


@app.route("/start-selected", methods=["POST"])
def start_selected():
    body = request.get_json()
    ads_power_profile_ids = body.get("adsPowerIds")
    if (
        ads_power_profile_ids is None
        or not isinstance(ads_power_profile_ids, list)
        or len(ads_power_profile_ids) <= 0
    ):
        return (
            jsonify(
                error="invalid_input",
                message="AdsPowerIds List not found",
            ),
            400,
        )

    agent_start_selected(ads_power_profile_ids)

    return {}


@app.route("/status")
def status():
    return app_status_info.get_all()


if __name__ == "__main__":
    app.run()
