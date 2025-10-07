from typing import Callable
from app.instagram.handlers.handler_context import HandlerContext
from app.status.profile_status_manager import ProfileStatusManager


class CheckpointHandler:
    shutdown_fn: Callable
    status_manager: ProfileStatusManager

    def __init__(
        self, shutdown_fn: Callable, status_manager: ProfileStatusManager
    ):
        self.shutdown_fn = shutdown_fn
        self.status_manager = status_manager
        pass

    def handle(self, context: HandlerContext):
        pass
