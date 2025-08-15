from app.instagram.handlers.base_handler import CheckpointHandler
from typing import Callable
from app.instagram.handlers.handler_context import HandlerContext
from app.status.profile_status_manager import ProfileStatusManager
from app.instagram.enums.checkpoint import Checkpoint
from app.airtable.enums.profile_status import AirtableProfileStatus
from app.status.profile_status_types import BotStatus


class AlreadyFollowedOrRequestedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.status_manager.increment_already_followed(
            context.profile.ads_power_id
        )
        if context.target not in context.processed_targets:
            context.processed_targets.append(context.target)
        return True


class PageFollowedOrRequestedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.status_manager.increment_total_followed(
            context.profile.ads_power_id
        )
        context.processed_targets.append(context.target)
        return True


class PageFollowedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.status_manager.increment_total_followed(
            context.profile.ads_power_id
        )
        context.processed_targets.append(context.target)
        return True


class PageRequestedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.status_manager.increment_total_followed(
            context.profile.ads_power_id
        )
        context.processed_targets.append(context.target)
        return True


class PageUnavailableHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.status_manager.increment_total_follow_failed(
            context.profile.ads_power_id
        )
        context.processed_targets.append(context.target)
        return True


class FailedToFollowHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.status_manager.increment_total_follow_failed(
            context.profile.ads_power_id
        )
        return True


class AccountSuspendedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.shutdown_fn(
            context.profile,
            context.driver,
            context.processed_targets,
            BotStatus.Banned,
        )
        context.profile.set_status(AirtableProfileStatus.Banned)
        return False


class AccountBannedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.shutdown_fn(
            context.profile,
            context.driver,
            context.processed_targets,
            BotStatus.Banned,
        )
        context.profile.set_status(AirtableProfileStatus.Banned)
        return False


class FollowBlockedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        context.profile.update_follow_limit_reached()
        self.shutdown_fn(
            context.profile,
            context.driver,
            context.processed_targets,
            BotStatus.FollowBlocked,
        )
        return False


class AccountLoggedOutHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.shutdown_fn(
            context.profile,
            context.driver,
            context.processed_targets,
            BotStatus.AccountLoggedOut,
        )
        context.profile.set_status(AirtableProfileStatus.LoggedOut)
        return False


class SomethingWentWrongHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.shutdown_fn(
            context.profile,
            context.driver,
            context.processed_targets,
            BotStatus.SomethingWentWrongHandler,
        )
        return False


class AccountCompromisedHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.shutdown_fn(
            context.profile,
            context.driver,
            context.processed_targets,
            BotStatus.SomethingWentWrongHandler,
        )
        context.profile.set_status(
            AirtableProfileStatus.ChangePasswordCheckpoint
        )
        return False


class BadProxyHandler(CheckpointHandler):
    def handle(self, context: HandlerContext):
        self.shutdown_fn(
            context.profile,
            context.driver,
            context.processed_targets,
            BotStatus.BadProxy,
        )
        context.profile.set_status(
            AirtableProfileStatus.ChangePasswordCheckpoint
        )
        return False


def create_handler_registry(
    shutdown_fn: Callable, status_manager: ProfileStatusManager
):
    registry = {
        Checkpoint.PageFollowed: PageFollowedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.PageRequested: PageRequestedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.AlreadyFollowedOrRequested: AlreadyFollowedOrRequestedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.PageFollowedOrRequested: PageFollowedOrRequestedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.PageUnavailable: PageUnavailableHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.FailedToFollow: FailedToFollowHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.AccountSuspended: AccountSuspendedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.AccountBanned: AccountBannedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.FollowBlocked: FollowBlockedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.AccountLoggedOut: AccountLoggedOutHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.SomethingWentWrongCheckpoint: SomethingWentWrongHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.AccountCompromised: AccountCompromisedHandler(
            shutdown_fn, status_manager
        ),
        Checkpoint.BadProxy: BadProxyHandler(shutdown_fn, status_manager),
    }
    return registry
