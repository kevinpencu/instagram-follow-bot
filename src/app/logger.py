import logging
import inspect
from app.config import get_cfg
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

if get_cfg()['settings']['logToFile']:
    log_file_path = "app.log"
    log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.INFO)
    
    sys.stdout = open(log_file_path, "a")
    sys.stderr = open(log_file_path, "a")


def get_logger():
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    return logging.getLogger(module.__name__ if module else "__main__")
