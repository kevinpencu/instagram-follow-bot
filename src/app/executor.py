from concurrent.futures import ThreadPoolExecutor
from app.constants import DEFAULT_WORKERS, DELAY_EXECUTOR_WORKERS


def get_executor(max_workers=DEFAULT_WORKERS):
    """Get a ThreadPoolExecutor with the specified max_workers"""
    return ThreadPoolExecutor(max_workers=max_workers)


# Default executor for backward compatibility
executor = get_executor()
delay_executor = get_executor(DELAY_EXECUTOR_WORKERS)
