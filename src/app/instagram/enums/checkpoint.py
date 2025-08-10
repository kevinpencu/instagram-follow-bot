from enum import Enum


class Checkpoint(str, Enum):
    BadProxy = "BadProxy"
    AccountCompromised = "AccountCompromised"
    SomethingWentWrongCheckpoint = "SomethingWentWrongCheckpoint"
    AutomaticBehaviourSuspected = "AutomaticBehaviourSuspected"
    AccountBanned = "AccountBanned"
    AccountSuspended = "AccountSuspended"
    AccountLoggedOut = "AccountLoggedOut"
    SaveLoginInfo = "SaveLoginInfo"
    PageFollowedOrRequested = "PageFollowedOrRequested"
    AlreadyFollowedOrRequested = "AlreadyFollowedOrRequested"
    PageUnavailable = "PageUnavailable"
    FailedToFollow = "FailedToFollow"
    FollowBlocked = "FollowBlocked"
