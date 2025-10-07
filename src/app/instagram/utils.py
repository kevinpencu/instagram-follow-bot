import time
from app.core.constants import RETRY_DELAYS


def delay_for_attempt(attempt_no: int = 1):
    if attempt_no not in RETRY_DELAYS:
        return False
    time.sleep(RETRY_DELAYS[attempt_no])
    return True
