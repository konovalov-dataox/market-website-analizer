import logging
from typing import Union


class LoggerFactory:
    _LOGGER = None

    @staticmethod
    def __create_logger(
            name: str,
            log_level: str = 'INFO',
            log_file: str = None,
    ) -> logging.Logger:
        LoggerFactory._LOGGER = logging.getLogger(name)

        logging.basicConfig(
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d%H:%M:%S',
            filename=log_file,
        )

        if log_level == "INFO":
            LoggerFactory._LOGGER.setLevel(logging.INFO)
        elif log_level == "ERROR":
            LoggerFactory._LOGGER.setLevel(logging.ERROR)
        elif log_level == "DEBUG":
            LoggerFactory._LOGGER.setLevel(logging.DEBUG)

        return LoggerFactory._LOGGER

    @staticmethod
    def get_logger(
            name: str,
            log_level: Union[str, int],
            log_file: str = None,
    ):
        logger = LoggerFactory.__create_logger(
            name=name,
            log_level=log_level,
            log_file=log_file,
        )
        return logger
