from app.airtable.models.profile import Profile
from app.executor import executor, get_executor, delay_executor
from app.status_module.profile_status_manager import (
    profile_status_manager,
)

class InstagramService:
    def __init__(self):
        pass

    def start_all(self, max_workers: int = 4):
        pass

    def start_selected(self, max_workers: int = 4):
        pass

    def stop_all(self, max_workers: int = 4):
        pass

    def run_single(self, profile: Profile):
        profile.refresh()
        pass


instagram_service = InstagramService()
