from logging import Logger
import logging


class LOGLEVEL():
    CRITICAL = 50
    ERROR    = 40
    WARNING  = 30
    INFO     = 20
    DEBUG    = 10
    NOTSET   = 0


def create_logger(logname: str,
                  base_level: int = LOGLEVEL.WARNING,
                  # stream_level=LOGLEVEL.INFO,
                  ) -> Logger:
    # format = f'%(levelname)s(%(name)s): %(message)s'
    logger = logging.getLogger(logname)
    logger.setLevel(base_level)
    # formatter = logging.Formatter(format)
    # stream = logging.StreamHandler()
    # stream.setLevel(stream_level)
    # stream.setFormatter(formatter)
    # logger.addHandler(stream)
    logger.propagate = False
    return logger


def get_all_mnms_logger() -> list[Logger]:
    return [logging.getLogger(name) for name in logging.root.manager.loggerDict if name.startswith('mnms')]


def get_logger(logger_name: str) -> Logger:
    return logging.getLogger(logger_name)


def set_mnms_logger_level(level: int, loggers: list[Logger] = []) -> None:
    [logging.getLogger(logger).setLevel(level) if isinstance(logger, str) else logger.setLevel(level) for logger in loggers]


def set_all_mnms_logger_level(level: int) -> None:
    set_mnms_logger_level(level, get_all_mnms_logger())


def attach_log_file(filename: str, file_level: int = LOGLEVEL.INFO) -> None:
    loggers = get_all_mnms_logger()
    file_handler = logging.FileHandler(filename, mode="w")
    file_handler.setLevel(file_level)
    format = f'%(levelname)s(%(name)s): %(message)s'
    formatter = logging.Formatter(format)
    file_handler.setFormatter(formatter)
    for l in loggers:
        l.addHandler(file_handler)
