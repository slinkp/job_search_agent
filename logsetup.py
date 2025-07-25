import logging
import os
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style
from colorama import init as colorama_init


class ColoredLogFormatter(logging.Formatter):
    """Custom formatter that adds colors based on log level"""

    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to the level name
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"

        # Add color to the module name
        record.name = f"{Fore.CYAN}{record.name}{Style.RESET_ALL}"

        return super().format(record)


class FileLogFormatter(logging.Formatter):
    """Custom formatter for file logging without colors"""

    def format(self, record):
        return super().format(record)


def setup_logging(verbose: bool = False, process_name: str = "main"):
    colorama_init()

    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Log file path
    log_file = os.path.join(log_dir, f"{process_name}.log")

    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        ColoredLogFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    # Create file handler with rotation (10MB max, 5 backup files)
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(
        FileLogFormatter(
            fmt="%(asctime)s [%(processName)s:%(process)d] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %Z",
        )
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
