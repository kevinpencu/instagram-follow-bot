import logging
import inspect

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_logger():
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    return logging.getLogger(module.__name__ if module else "__main__")
