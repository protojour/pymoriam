import sys
import os

from pathlib import Path

from memoriam.logs import init_logging_config
from memoriam.utils import load_yaml


ROOT_PATH = os.getenv('ROOT_PATH', Path(__file__, '..').resolve())


def test_init_logging_config_default_logging_config():
    config_path = Path(ROOT_PATH, '..', 'memoriam', 'data', 'logging_config.yml')
    config_dict = load_yaml(path=config_path)
    assert config_dict['handlers']['console']['stream'] == 'sys.stdout', \
        f"String 'sys.stdout' expected before init_logging_config() called. Got: {config_dict['handlers']['console']['stream']}"
    init_logging_config(config_dict)
    assert config_dict['handlers']['console']['stream'] != 'sys.stdout', \
        "Expecting not a string 'sys.stdout' after init_logging_config() is called"
    assert config_dict['handlers']['console']['stream'] == sys.stdout, \
        f"Expecting sys.stdout. Got {config_dict['handlers']['console']['stream']}"
    assert config_dict['handlers']['console_error']['stream'] != 'sys.stderr', \
        "Expecting not a string 'sys.stderr' after init_logging_config() is called"
    assert config_dict['handlers']['console_error']['stream'] == sys.stderr, \
        f"Expecting sys.stderr. Got {config_dict['handlers']['console_error']['stream']}"
    assert config_dict['loggers']['memoriam.aql']['handlers'] == [], \
        f"Expecting []. Got {config_dict['loggers']['memoriam.aql']['handlers']}"
    assert config_dict['loggers']['memoriam.audit']['handlers'] == [], \
        f"Expecting []. Got {config_dict['loggers']['memoriam.audit']['handlers']}"
    assert config_dict['loggers']['memoriam.error']['handlers'] == ['console_error'], \
        f"Expecting ['console_error']. Got {config_dict['loggers']['memoriam.error']['handlers']}"
    assert config_dict['loggers']['memoriam.perf']['handlers'] == [], \
        f"Expecting []. Got {config_dict['loggers']['memoriam.perf']['handlers'] }"


def test_init_logging_config_logging_config_2():
    config_path = Path(ROOT_PATH, 'data', 'test_logging_config.yml')
    config_dict = load_yaml(path=config_path)
    init_logging_config(config_dict)
    assert config_dict['handlers']['console']['stream'] is None, \
        f"Expecting None. Got {config_dict['handlers']['console']['stream']}"
    assert config_dict['handlers']['console']['stream'] != 'sys.stderr', \
        f"Expecting not string 'sys.stdout'. Got {config_dict['handlers']['console']['stream']}"
    assert config_dict['handlers']['console_err']['stream'] != 'sys.stderr', \
        f"Expecting not string 'sys.stderr'. Got {config_dict['handlers']['console_err']['stream']}"
    assert config_dict['handlers']['console_err']['stream'] == sys.stderr, \
        f"Expecting sys.stderr. Got {config_dict['handlers']['console_err']['stream']}"
    assert config_dict['loggers']['memoriam.aql']['handlers'] == [], \
        f"Expecting []. Got {config_dict['loggers']['memoriam.aql']['handlers']}"
    assert config_dict['loggers']['memoriam.audit']['handlers'] == [], \
        f"Expecting []. Got {config_dict['loggers']['memoriam.audit']['handlers']}"
    assert config_dict['loggers']['memoriam.error']['handlers'] == ['console_err'], \
        f"Expecting ['console_err']. Got {config_dict['loggers']['memoriam.error']['handlers']}"
    assert config_dict['loggers']['memoriam.perf']['handlers'] == [], \
        f"Expecting []. Got {config_dict['loggers']['memoriam.perf']['handlers']}"
