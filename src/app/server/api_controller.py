from flask import jsonify, request
from app.airtable.profile_repository import AirTableProfileRepository
from app.insta_module.instagram_service import instagram_service
from app.status_module.profile_status_manager import (
    profile_status_manager,
)
import traceback


class MainApiController:
    def __init__(self):
        pass

    # helper method
    def get_max_workers(self):
        body = request.get_json() or {}
        return body.get("maxWorkers", 4)

    # helper method
    def get_adspowerids(self):
        body = request.get_json() or {}
        ads_power_profile_ids = body.get("adsPowerIds")
        if (
            ads_power_profile_ids is None
            or not isinstance(ads_power_profile_ids, list)
            or len(ads_power_profile_ids) <= 0
        ):
            return None

        return ads_power_profile_ids

    def get_profiles(self):
        try:
            return AirTableProfileRepository().get_profiles()
        except Exception as e:
            return (
                jsonify(
                    error="internal_error",
                    message=f"Failed to fetch profiles {str(e)} \n {traceback.format_exc()}",
                ),
                500,
            )

    def stop_all(self):
        try:
            instagram_service.stop_all()
        except Exception as e:
            # Log Stop All Failed
            pass

        return None

    def start_all(self):
        try:
            instagram_service.start_all(self.get_max_workers())
        except Exception as e:
            return (
                jsonify(
                    error="internal_error",
                    message=f"Start All Failed {str(e)} \n {traceback.format_exc}",
                ),
                500,
            )

        return None

    def start_selected(self):
        try:
            instagram_service.start_selected(
                self.get_adspowerids(), self.get_max_workers()
            )
        except Exception as e:
            return (
                jsonify(
                    error="internal_error",
                    message=f"Start Selected Failed {str(e)} \n {traceback.format_exc}",
                ),
                500,
            )

        return None

    def status(self):
        try:
            return profile_status_manager.get_route_data()
        except Exception as e:
            return (
                jsonify(
                    error="internal_error",
                    message=f"Status Get Failed {str(e)} \n {traceback.format_exc}",
                ),
                500,
            )


main_api_controller = MainApiController()
