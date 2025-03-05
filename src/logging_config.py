import datetime as dt
import logging
import logging.config
import os

# Get the root directory of the project
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)  # Ensure the log directory exists


def setup_logging():
    # Create a timestamp for the log file name. Format: YYYYMMDD
    timestamp = dt.datetime.now().strftime("%Y%m%d")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "detailed": {  # Formatter for detailed exception logs
                    "format": (
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s\n"
                        "---[Exception]---\n%(exc_info)s"
                    ),
                },
                "console": {  # Formatter for console output
                    "format": "%(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "info_file_handler": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "filename": os.path.join(LOG_DIR, f"info_{timestamp}.log"),
                    "when": "midnight",  # Rotate at midnight
                    "interval": 1,  # Every day
                    "backupCount": 5,  # Keep 5 backups
                    "level": "INFO",
                    "formatter": "default",
                    "encoding": "utf-8",
                },
                "error_file_handler": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "filename": os.path.join(LOG_DIR, f"error_{timestamp}.log"),
                    "when": "midnight",  # Rotate at midnight
                    "interval": 1,  # Every day
                    "backupCount": 5,  # Keep 5 backups
                    "level": "ERROR",
                    "formatter": "detailed",
                    "encoding": "utf-8",
                },
                "console_handler": {  # StreamHandler for console output
                    "class": "logging.StreamHandler",
                    "level": "INFO",  # Show all logs in the console
                    "formatter": "console",
                },
            },
            "loggers": {
                # Set up root logger to capture all logs at INFO level
                "": {
                    "level": "INFO",
                    "handlers": [
                        "info_file_handler",
                        "error_file_handler",
                        "console_handler",
                    ],
                    "propagate": True,
                },
                # Set up logger specifically for pyrogram with INFO level
                "pyrogram": {
                    "level": "INFO",  # Set Pyrogram logs to INFO level
                    "handlers": [
                        "info_file_handler",
                        "error_file_handler",
                        "console_handler",
                    ],
                    "propagate": True,
                },
                # Additional loggers can be configured here as needed
            },
        }
    )
