import sys
import logging
import logging.config

from memoriam import config


def init_logging_config(config_dict):

    for handler in config_dict.get('handlers', {}).values():
        if handler.get('class') == 'logging.StreamHandler':
            stream_name = handler.get('stream')

            if stream_name == 'sys.stdout':
                handler['stream'] = sys.stdout

            if stream_name == 'sys.stderr':
                handler['stream'] = sys.stderr

    for logger_name, logger in config_dict.get('loggers').items():

        if config.DEBUG:
            logger['level'] = config.LOG_LEVEL
        elif config.LOG_LEVEL != 'INFO':
            logger['level'] = config.LOG_LEVEL

        if logger_name in ('memoriam.error', 'sanic.error') and not config.ERROR_LOG:
            logger['handlers'] = []

        if logger_name == 'sanic.access' and not config.ACCESS_LOG:
            logger['handlers'] = []

        if logger_name == 'memoriam.aql' and not config.AQL_LOG:
            logger['handlers'] = []

        if logger_name == 'memoriam.audit' and not config.AUDIT_LOG:
            logger['handlers'] = []

        if logger_name == 'memoriam.perf' and not config.PERF_LOG:
            logger['handlers'] = []

    logging.config.dictConfig(config_dict)
