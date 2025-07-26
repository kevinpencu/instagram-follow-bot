from concurrent.futures import ThreadPoolExecutor

def get_executor(max_workers=4):
    """Get a ThreadPoolExecutor with the specified max_workers"""
    return ThreadPoolExecutor(max_workers=max_workers)

# Default executor for backward compatibility
executor = get_executor()
