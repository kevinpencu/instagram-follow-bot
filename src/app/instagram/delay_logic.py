import time


def delay_for_attempt(attempt_no: int = 1):
    attempts_delay_map = {0: 0, 1: 0, 2: 10, 3: 60, 4: 300}
    if attempt_no not in attempts_delay_map:
        return False
    time.sleep(attempts_delay_map[attempt_no])
    return True
