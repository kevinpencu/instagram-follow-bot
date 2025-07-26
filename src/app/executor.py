from concurrent.futures import ThreadPoolExecutor

# Limit max workers to prevent resource exhaustion
executor = ThreadPoolExecutor(max_workers=10)
