from app.airtable.helper import (
    get_profiles,
    get_profiles_mapped,
)
from flask import Flask, request, jsonify
from app.adspower.api_wrapper import adspower
from app.app_status_info import app_status_info
from app.executor import executor, get_executor
from app.insta_agent import agent_start_all, agent_start_selected
from app.logger import get_logger
from flask_cors import CORS
from app.errors import init_handler

app = Flask(__name__)
CORS(app)
init_handler(app)


@app.route("/profiles")
def profiles():
    try:
        return get_profiles_mapped()
    except Exception as e:
        get_logger().error(f"[API]: Failed to get profiles: {str(e)}")
        return (
            jsonify(
                error="internal_error", message="Failed to fetch profiles"
            ),
            500,
        )


@app.route("/start-all", methods=["POST"])
def start():
    try:
        body = request.get_json() or {}
        max_workers = body.get("maxWorkers", 4)

        if not isinstance(max_workers, int) or max_workers <= 0:
            return (
                jsonify(
                    error="invalid_input",
                    message="maxWorkers must be a positive integer",
                ),
                400,
            )

        agent_start_all(max_workers)
        return {}
    except Exception as e:
        get_logger().error(f"[API]: Failed to start all agents: {str(e)}")
        return (
            jsonify(
                error="internal_error", message="Failed to start agents"
            ),
            500,
        )


@app.route("/start-selected", methods=["POST"])
def start_selected():
    try:
        body = request.get_json()
        if body is None:
            return (
                jsonify(
                    error="invalid_input",
                    message="Request body is required",
                ),
                400,
            )

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

        max_workers = body.get("maxWorkers", 4)

        if not isinstance(max_workers, int) or max_workers <= 0:
            return (
                jsonify(
                    error="invalid_input",
                    message="maxWorkers must be a positive integer",
                ),
                400,
            )

        agent_start_selected(ads_power_profile_ids, max_workers)
        return {}
    except Exception as e:
        get_logger().error(
            f"[API]: Failed to start selected agents: {str(e)}"
        )
        return (
            jsonify(
                error="internal_error",
                message="Failed to start selected agents",
            ),
            500,
        )


@app.route("/status")
def status():
    try:
        return app_status_info.get_all()
    except Exception as e:
        get_logger().error(f"[API]: Failed to get status: {str(e)}")
        return (
            jsonify(
                error="internal_error", message="Failed to fetch status"
            ),
            500,
        )


if __name__ == "__main__":
    app.run()
