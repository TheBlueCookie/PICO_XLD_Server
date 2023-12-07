from logging.handlers import TimedRotatingFileHandler
import logging



log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
xld_logger = logging.getLogger("XLD Logger")




