#
# Copyright 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""This module provides log functionalities."""

import logging
import logging.handlers
import os.path as op
import traceback
from functools import partial
from threading import Lock
from typing import Dict, Any

from .pattern import Singleton
from .splunkenv import make_splunkhome_path

__all__ = ["log_enter_exit", "LogException", "Logs"]


def log_enter_exit(logger: logging.Logger):
    """Decorator for logger to log function enter and exit.

    This decorator will generate a lot of debug log, please add this
    only when it is required.

    Arguments:
        logger: Logger to decorate.

    Examples:
        >>> @log_enter_exit
        >>> def myfunc():
        >>>     doSomething()
    """

    def log_decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug("%s entered", func.__name__)
            result = func(*args, **kwargs)
            logger.debug("%s exited", func.__name__)
            return result

        return wrapper

    return log_decorator


class LogException(Exception):
    """Exception raised by Logs class."""

    pass


class Logs(metaclass=Singleton):
    """A singleton class that manage all kinds of logger.

    Examples:
      >>> from solnlib import log
      >>> log.Logs.set_context(directory='/var/log/test',
                               namespace='test')
      >>> logger = log.Logs().get_logger('mymodule')
      >>> logger.set_level(logging.DEBUG)
      >>> logger.debug('a debug log')
    """

    # Normal logger settings
    _default_directory = None
    _default_namespace = None
    _default_log_format = (
        "%(asctime)s log_level=%(levelname)s pid=%(process)d tid=%(threadName)s "
        "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
    )
    _default_log_level = logging.INFO
    _default_max_bytes = 25000000
    _default_backup_count = 5

    # Default root logger settings
    _default_root_logger_log_file = "solnlib"

    @classmethod
    def set_context(cls, **context: dict):
        """Set log context.

        List of keyword arguments:

            directory: Log directory, default is splunk log root directory.
            namespace: Logger namespace, default is None.
            log_format: Log format, default is `_default_log_format`.
            log_level: Log level, default is logging.INFO.
            max_bytes: The maximum log file size before rollover, default is 25000000.
            backup_count: The number of log files to retain,default is 5.
            root_logger_log_file: Root logger log file name, default is 'solnlib'   .

        Arguments:
            context: Keyword arguments. See list of arguments above.
        """
        if "directory" in context:
            cls._default_directory = context["directory"]
        if "namespace" in context:
            cls._default_namespace = context["namespace"]
        if "log_format" in context:
            cls._default_log_format = context["log_format"]
        if "log_level" in context:
            cls._default_log_level = context["log_level"]
        if "max_bytes" in context:
            cls._default_max_bytes = context["max_bytes"]
        if "backup_count" in context:
            cls._default_backup_count = context["backup_count"]
        if "root_logger_log_file" in context:
            cls._default_root_logger_log_file = context["root_logger_log_file"]
            cls._reset_root_logger()

    @classmethod
    def _reset_root_logger(cls):
        logger = logging.getLogger()
        log_file = cls._get_log_file(cls._default_root_logger_log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            mode="a",
            maxBytes=cls._default_max_bytes,
            backupCount=cls._default_backup_count,
        )
        file_handler.setFormatter(logging.Formatter(cls._default_log_format))
        logger.addHandler(file_handler)
        logger.setLevel(cls._default_log_level)

    @classmethod
    def _get_log_file(cls, name):
        if cls._default_namespace:
            name = f"{cls._default_namespace}_{name}.log"
        else:
            name = f"{name}.log"

        if cls._default_directory:
            directory = cls._default_directory
        else:
            try:
                directory = make_splunkhome_path(["var", "log", "splunk"])
            except KeyError:
                raise LogException(
                    "Log directory is empty, please set log directory "
                    'by calling Logs.set_context(directory="/var/log/...").'
                )
        log_file = op.sep.join([directory, name])

        return log_file

    def __init__(self):
        self._lock = Lock()
        self._loggers = {}

    def get_logger(self, name: str) -> logging.Logger:
        """Get logger with the name of `name`.

        If logger with the name of `name` exists just return else create a new
        logger with the name of `name`.

        Arguments:
            name: Logger name, it will be used as log file name too.

        Returns:
            A named logger.
        """

        with self._lock:
            log_file = self._get_log_file(name)
            if log_file in self._loggers:
                return self._loggers[log_file]

            logger = logging.getLogger(log_file)
            handler_exists = any(
                [True for h in logger.handlers if h.baseFilename == log_file]
            )
            if not handler_exists:
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    mode="a",
                    maxBytes=self._default_max_bytes,
                    backupCount=self._default_backup_count,
                )
                file_handler.setFormatter(logging.Formatter(self._default_log_format))
                logger.addHandler(file_handler)
                logger.setLevel(self._default_log_level)
                logger.propagate = False

            self._loggers[log_file] = logger
            return logger

    def set_level(self, level: int, name: str = None):
        """Set log level of logger.

        Set log level of all logger if `name` is None else of
        logger with the name of `name`.

        Arguments:
            level: Log level to set.
            name: The name of logger, default is None.
        """

        with self._lock:
            if name:
                log_file = self._get_log_file(name)
                logger = self._loggers.get(log_file)
                if logger:
                    logger.setLevel(level)
            else:
                self._default_log_level = level
                for logger in list(self._loggers.values()):
                    logger.setLevel(level)
                logging.getLogger().setLevel(level)


def log_event(
    logger: logging.Logger, key_values: Dict[str, Any], log_level: int = logging.INFO
):
    """General function to log any event in key-value format."""
    message = " ".join([f"{k}={v}" for k, v in key_values.items()])
    logger.log(log_level, message)


def modular_input_start(logger: logging.Logger, modular_input_name: str):
    """Specific function to log the start of the modular input."""
    log_event(
        logger,
        {
            "action": "started",
            "modular_input_name": modular_input_name,
        },
    )


def modular_input_end(logger: logging.Logger, modular_input_name: str):
    """Specific function to log the end of the modular input."""
    log_event(
        logger,
        {
            "action": "ended",
            "modular_input_name": modular_input_name,
        },
    )


def _base_error_log(
    logger,
    exc: Exception,
    exe_label,
    full_msg: bool = True,
    msg_before: str = None,
    msg_after: str = None,
):
    log_exception(
        logger,
        exc,
        exc_label=exe_label,
        full_msg=full_msg,
        msg_before=msg_before,
        msg_after=msg_after,
    )


log_connection_error = partial(_base_error_log, exe_label="Connection Error")
log_configuration_error = partial(_base_error_log, exe_label="Configuration Error")
log_permission_error = partial(_base_error_log, exe_label="Permission Error")
log_authentication_error = partial(_base_error_log, exe_label="Authentication Error")
log_server_error = partial(_base_error_log, exe_label="Server Error")


def events_ingested(
    logger: logging.Logger,
    modular_input_name: str,
    sourcetype: str,
    n_events: int,
    index: str,
    account: str = None,
    host: str = None,
    license_usage_source: str = None,
):
    """Specific function to log the basic information of events ingested for
    the monitoring dashboard.

    Arguments:
        logger: Add-on logger.
        modular_input_name: Full name of the modular input. It needs to be in a format `<input_type>://<input_name>`.
            In case of invalid format ValueError is raised.
        sourcetype: Source type used to write event.
        n_events: Number of ingested events.
        index: Index used to write event.
        license_usage_source: source used to match data with license_usage.log.
        account: Account used to write event. (optional)
        host: Host used to write event. (optional)
    """

    if "://" in modular_input_name:
        input_name = modular_input_name.split("/")[-1]
    else:
        raise ValueError(
            f"Invalid modular input name: {modular_input_name}. "
            f"It should be in format <input_type>://<input_name>"
        )

    result = {
        "action": "events_ingested",
        "modular_input_name": license_usage_source
        if license_usage_source
        else modular_input_name,
        "sourcetype_ingested": sourcetype,
        "n_events": n_events,
        "event_input": input_name,
        "event_index": index,
    }

    if account:
        result["event_account"] = account

    if host:
        result["event_host"] = host

    log_event(logger, result)


def log_exception(
    logger: logging.Logger,
    e: Exception,
    exc_label: str,
    full_msg: bool = True,
    msg_before: str = None,
    msg_after: str = None,
    log_level: int = logging.ERROR,
):
    """General function to log exceptions.

    Arguments:
        logger: Add-on logger.
        e: Exception to log.
        exc_label: label for the error to categorize it.
        full_msg: if set to True, full traceback will be logged. Default: True
        msg_before: custom message before exception traceback. Default: None
        msg_after: custom message after exception traceback. Default: None
        log_level: Log level to log exception. Default: ERROR.
    """

    msg = _get_exception_message(e, full_msg, msg_before, msg_after)
    logger.log(log_level, f'exc_l="{exc_label}" {msg}')


def _get_exception_message(
    e: Exception,
    full_msg: bool = True,
    msg_before: str = None,
    msg_after: str = None,
) -> str:
    exc_type, exc_value, exc_traceback = type(e), e, e.__traceback__
    if full_msg:
        error = traceback.format_exception(exc_type, exc_value, exc_traceback)
    else:
        error = traceback.format_exception_only(exc_type, exc_value)

    msg_start = msg_before if msg_before is not None else ""
    msg_mid = "".join(error)
    msg_end = msg_after if msg_after is not None else ""
    return f"{msg_start}\n{msg_mid}\n{msg_end}"
