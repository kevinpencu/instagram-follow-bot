import time
from app.airtable.profile_repository import AirTableProfileRepository
from app.airtable.enums.profile_status import AirtableProfileStatus
from app.airtable.models.profile import Profile
from app.insta.instagram_selenium import InstagramWrapper
from app.adspower.api_wrapper import adspower
from app.executor import executor, get_executor, delay_executor
from app.adspower_selenium import run_selenium
from app.insta.enums.checkpoint import Checkpoint
from app.status_module.profile_status_manager import (
    profile_status_manager,
)
from app.status_module.profile_status_types import BotStatus

attempts_delay_map = {1: 0, 2: 10, 3: 60, 4: 300}


def run_single(profile: Profile, attempt_no: int = 1):
    profile.refresh()

    if profile_status_manager.should_stop(profile.ads_power_id):
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Done
        )
        return

    if attempt_no in attempts_delay_map:
        time.sleep(attempts_delay_map[attempt_no])
    else:
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Failed
        )
        return

    try:
        profile_status_manager.init_profile(profile)

        usernames = profile.download_targets()

        # ERROR-CODE: No Usernames Found
        if len(usernames) <= 0:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.NoTargets
            )
            return

        start_profile_response = adspower.start_profile(
            profile.ads_power_id
        )

        # ERROR-CODE: Profile Start Failed
        if start_profile_response is None:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.AdsPowerStartFailed
            )
            delay_executor.submit(run_single, profile, attempt_no + 1)
            return

        time.sleep(3)

        try:
            selenium_instance = run_selenium(start_profile_response)
        except Exception as e:
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.SeleniumFailed
            )
            return

        profile_status_manager.set_total(
            profile.ads_power_id, len(usernames)
        )
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Running
        )

        processed_usernames = profile.download_processed_targets()
        for username in usernames:
            if profile_status_manager.should_stop(profile.ads_power_id):
                break

            if username in processed_usernames:
                profile_status_manager.increment_already_followed(
                    profile.ads_power_id
                )
                continue

            result = InstagramWrapper(selenium_instance).follow_action(
                username
            )
            if result == Checkpoint.AlreadyFollowedOrRequested:
                profile_status_manager.increment_already_followed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == Checkpoint.PageFollowedOrRequested:
                profile_status_manager.increment_total_followed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == Checkpoint.PageUnavailable:
                profile_status_manager.increment_total_follow_failed(
                    profile.ads_power_id
                )
                processed_usernames.append(username)
                continue

            if result == Checkpoint.FailedToFollow:
                profile_status_manager.increment_total_follow_failed(
                    profile.ads_power_id
                )
                continue

            if result == Checkpoint.AccountSuspended:
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.AccountIsSuspended
                )
                break

            if result == Checkpoint.AccountBanned:
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.Banned
                )

                # Update Airtable status to "Banned"
                profile.set_status(AirtableProfileStatus.Banned)
                break

            if result == Checkpoint.FollowBlocked:
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.FollowBlocked
                )
                # Update Airtable with the follow limit reached timestamp
                profile.update_follow_limit_reached()
                break

            if result == Checkpoint.AccountLoggedOut:
                profile_status_manager.set_status(
                    profile.ads_power_id, BotStatus.AccountLoggedOut
                )
                # Update Airtable status to "Logged Out"
                profile.set_status(AirtableProfileStatus.LoggedOut)
                break

            if result == Checkpoint.SomethingWentWrongCheckpoint:
                profile_status_manager.set_status(
                    profile.ads_power_id,
                    BotStatus.SomethingWentWrong,
                )

                # Update Airtable status to "SomethingWentWrongCheckpoint"
                profile.set_status(
                    AirtableProfileStatus.SomethingWentWrongCheckpoint
                )
                break

            if result == Checkpoint.AccountCompromised:
                profile_status_manager.set_status(
                    profile.ads_power_id,
                    BotStatus.AccountCompromised,
                )

                # Update Airtable status to "ChangePasswordCheckpoint"
                profile.set_status(
                    AirtableProfileStatus.ChangePasswordCheckpoint
                )
                break

            if result == Checkpoint.BadProxy:
                profile_status_manager.set_status(
                    profile.ads_power_id,
                    BotStatus.BadProxy,
                )

                # Update Airtable status to "BadProxy"
                profile.set_status(AirtableProfileStatus.BadProxy)
                break

        profile.update_processed_targets(processed_usernames)
        current_profile_stats = profile_status_manager.get_profile_stats(
            profile.ads_power_id
        )
        if (
            current_profile_stats is not None
            and current_profile_stats.is_ok()
        ):
            profile_status_manager.set_status(
                profile.ads_power_id, BotStatus.Done
            )

    except Exception as e:
        profile_status_manager.set_status(
            profile.ads_power_id, BotStatus.Failed
        )
        delay_executor.submit(run_single, profile, attempt_no + 1)
    finally:
        profile.update_processed_targets(processed_usernames)

        try:
            selenium_instance.quit()
        except Exception as e:
            pass

        try:
            adspower.stop_profile(profile.ads_power_id)
        except Exception as e:
            pass


def do_start_profiles(profiles: list[Profile], max_workers=4):
    for profile in profiles:
        profile_status_manager.schedule_profile(profile.ads_power_id)

    profile_executor = get_executor(max_workers)
    for profile in profiles:
        profile_executor.submit(run_single, profile)
        time.sleep(1)


def do_start_all(max_workers: int = 4):
    profiles = AirTableProfileRepository().get_profiles()
    do_start_profiles(profiles, max_workers)


def do_start_selected(ads_power_ids: list[str], max_workers: int = 4):
    all_profiles = AirTableProfileRepository().get_profiles()
    selected_profiles = [
        profile
        for profile in all_profiles
        if profile.ads_power_id in ads_power_ids
    ]

    if len(selected_profiles) == 0:
        return

    do_start_profiles(selected_profiles, max_workers)


def agent_start_all(max_workers=4):
    executor.submit(do_start_all, max_workers)


def agent_start_selected(ads_power_ids: list, max_workers=4):
    executor.submit(do_start_selected, ads_power_ids, max_workers)


def agent_stop():
    profile_status_manager.stop_all()
