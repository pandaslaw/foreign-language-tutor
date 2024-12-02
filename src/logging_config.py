import logging
import logging.config
import os

# Get the root directory of the project
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))


def setup_logging():
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
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(ROOT_DIR, "logs//info.log"),
                    "maxBytes": 10 * 1024 * 1024,  # 10 MB
                    "backupCount": 5,  # Keep 5 backups
                    "level": "INFO",
                    "formatter": "default",
                    "encoding": "utf-8",
                },
                "error_file_handler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(ROOT_DIR, "logs//error.log"),
                    "maxBytes": 5 * 1024 * 1024,  # 5 MB
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
                "": {  # Root logger
                    "level": "DEBUG",
                    "handlers": [
                        "info_file_handler",
                        "error_file_handler",
                        "console_handler",
                    ],
                },
                "httpx": {
                    "level": "WARNING",
                    "handlers": [
                        "console_handler"
                    ],  # Optional: Still print important logs
                    "propagate": False,
                },
            },
        }
    )
