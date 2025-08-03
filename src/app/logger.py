import logging
import inspect
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

log_file = 'app.log'
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

logging.getLogger().addHandler(file_handler)
logging.getLogger().setLevel(logging.DEBUG)

sys.stdout = open(log_file, 'a')
sys.stderr = open(log_file, 'a')


def get_logger():
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    return logging.getLogger(module.__name__ if module else "__main__")
