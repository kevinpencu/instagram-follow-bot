from enum import Enum


class Checkpoint(int, Enum):
    BadProxy = 0
    AccountCompromised = 1
    SomethingWentWrongCheckpoint = 2
    AutomaticBehaviourSuspected = 3
    AccountBanned = 4
    AccountSuspended = 5
    AccountLoggedOut = 6
    SaveLoginInfo = 7
    PageFollowedOrRequested = 8
    AlreadyFollowedOrRequested = 9
    PageUnavailable = 10
    FailedToFollow = 11
    FollowBlocked = 12
