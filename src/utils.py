import os
import time
import base64
import secrets
import hashlib
import datetime
import pathlib
import logging
import logging.config


def init_logger(
    name: str,
    log_debug_filename: str = "debug.log",
    log_info_filename: str = "info.log",
) -> logging.Logger:
    here = pathlib.Path(__file__).parent.absolute()
    logs_path = here.joinpath("logs")
    if not os.path.isdir(logs_path):
        os.makedirs(logs_path, exist_ok=True)

    logging_config = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] - %(levelname)8s - %(filename)s - %(message)s",
            },
            "detailed": {
                "format": (
                    # "[%(asctime)s] - %(levelname)8s - [%(filename)s:%(funcName)s:%(lineno)d]"
                    # " - [%(process)d:%(processName)s | %(thread)d:%(threadName)s] - %(message)s"
                    "[%(asctime)s] - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d]"
                    " - [%(process)d:%(processName)s | %(thread)d:%(threadName)s] - %(message)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "detailed",
                "level": "DEBUG",
            },
            "logfile": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "formatter": "detailed",
                "filename": os.path.join(logs_path, log_info_filename),
                "mode": "a",
            },
            "debuglogfile": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": os.path.join(logs_path, log_debug_filename),
                "mode": "a",
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 1000,
            },
        },
        "loggers": {
            "": {"handlers": ["debuglogfile", "console", "logfile"], "level": "DEBUG"},
        },
    }
    logging.Formatter.converter = time.gmtime
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(name)
    logger.info("Logging setup executed.")
    return logger


def generate_hash(password=None, salt=None):
    """
    Generates a salted hash from a password.

    Helps create new users.

    Args:
        password (str): Password to hash.
        salt (str): Salt string.

    Returns:
        str
    """
    if not password:
        raise Exception("Password needs to be provided.")
    if not salt:
        salt = secrets.token_bytes(32)
    hashed_password = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, 1000000)
    return "{impl}${iterations}${salt}${pwd}".format(
        impl="pbkdf2_hmac_sha512",
        iterations=1000000,
        salt=base64.b64encode(salt).decode(),
        pwd=base64.b64encode(hashed_password).decode(),
    )


def authenticate(user, password):
    """
    Authenticates a user:password combination.

    Args:
        user (str): Username
        password (str): Password

    Returns:
        bool - True if successfully authenticated
    """
    credentials = {
        "user": "pbkdf2_hmac_sha512$1000000$2AwaqCGv4wpgsDmnCq5MDCvfumBSTzEFoUNOErpryvQ=$yJGRGzdx1E9SZKr3RuMOjg7B1yCbLaXS9lJN3v9Im+/K2Md9YjjzOjlkLURRENVq317s/gvwsUHiKKg5ICxWSA==",
    }
    if user in credentials:
        hashed_password = credentials.get(user)
        salt = hashed_password.split("$")[2]
        return (
            generate_hash(password=password, salt=base64.b64decode(salt))
            == hashed_password
        )
    else:
        return False


def get_previous_day(day_name, start_date=None):
    """
    Compute a datetime object that is the previous day_name provided

    Arguments:
        day_name (str): Written day name
        start_date (datetime.datetime): Initial date to consider - previous day_name from this date will be produced.

    Returns:
        datetime.datetime

    Example:
        >>> get_previous_day('monday', start_date=datetime.datetime(2018, 2, 27, 10, 49, 7, 992699))
        datetime.datetime(2018, 2, 26, 10, 49, 7, 992699)
    """
    weekdays = [
        i.lower()
        for i in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
    ]
    if start_date is None:
        start_date = datetime.datetime.today()
    day_num = start_date.weekday()
    day_num_target = weekdays.index(day_name.lower())
    days_ago = (7 + day_num - day_num_target) % 7
    if days_ago == 0:
        days_ago = 7
    target_date = start_date - datetime.timedelta(days=days_ago)
    return target_date


def get_next_day(day_name, start_date=None):
    """
    Compute a datetime object that is the next day_name of the start_date provided (today if start_date is not specified)

    Arguments:
        day_name (str): Written day name
        start_date (datetime.datetime): Initial date to consider - next day_name from this date will be produced.

    Returns:
        datetime.datetime

    Example:
        >>> get_next_day('monday')
        datetime.datetime(2018, 3, 5, 17, 37, 2, 121058)
    """
    weekdays = [
        i.lower()
        for i in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
    ]
    if start_date is None:
        start_date = datetime.datetime.today()
    day_num = start_date.weekday()
    day_num_target = weekdays.index(day_name.lower())
    days = (7 - day_num + day_num_target) % 7
    if days == 0:
        days = 7
    target_date = start_date + datetime.timedelta(days=days)
    return target_date


def previous_weekday(date=None):
    """
    Utility to return a datetime object from the previous weekday from <date>.

    Parameters:
        date (datetime.datetime): Date to use as base for computing the previous weekday.

    Example:
        >>> previous_weekday()
        datetime.datetime(2018, 2, 27, 10, 50, 10, 419704)
    """
    if date is None:
        date = datetime.datetime.today()
    date -= datetime.timedelta(days=1)
    while date.weekday() > 4:  # Mon-Fri are 0-4
        date -= datetime.timedelta(days=1)
    return date


def next_weekday(date=None):
    """
    Utility to return a datetime object from the previous weekday from <date>.

    Parameters:
        date (datetime.datetime): Date to use as base for computing the next weekday.

    Example:
        >>> next_weekday()
        datetime.datetime(2018, 3, 5, 18, 14, 42, 676370)
    """
    if date is None:
        date = datetime.datetime.today()
    date += datetime.timedelta(days=1)
    while date.weekday() > 4:  # Mon-Fri are 0-4
        date += datetime.timedelta(days=1)
    return date
