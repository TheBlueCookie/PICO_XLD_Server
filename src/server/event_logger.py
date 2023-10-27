from logging.handlers import TimedRotatingFileHandler
import logging

log_file = "xld_events.log"

log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
xld_logger = logging.getLogger("XLD Logger")

file_handler = TimedRotatingFileHandler(log_file, when='W0')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)
xld_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)
xld_logger.addHandler(console_handler)

flask_file_handler = TimedRotatingFileHandler("flask_events.log", when='W0')
flask_file_handler.setFormatter(log_formatter)
flask_file_handler.setLevel(logging.INFO)
