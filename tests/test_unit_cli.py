from unittest.mock import patch

import pytest

from click.testing import CliRunner
from memoriam.cli import *


@pytest.fixture
def runner():
    return CliRunner()


def test_memoriam(runner):
    result = runner.invoke(memoriam)
    assert result.exit_code == 0


def test_memoriam_gateway(runner):
    with patch('memoriam.cli.init_gateway') as init:
        # FIXME: doesn't actually run
        result = runner.invoke(memoriam, ['gateway'])
        assert init.return_value.run.called_once()


def test_memoriam_domain(runner):
    with patch('memoriam.cli.init_domain') as init:
        # FIXME: doesn't actually run
        result = runner.invoke(memoriam, ['domain'])
        assert init.return_value.run.called_once()


def test_memoriam_storage(runner):
    with patch('memoriam.cli.init_storage') as init:
        # FIXME: doesn't actually run
        result = runner.invoke(memoriam, ['storage'])
        assert init.return_value.run.called_once()


def test_memoriam_config(runner):
    with patch('memoriam.cli.config') as init:
        result = runner.invoke(memoriam, ['config'])
        assert init.return_value.run.called_one()


def test_memoriam_config_db(runner):
    assert runner.invoke(config, ['--db']).output == Path('memoriam/data/db_schema.yml').resolve().read_text()+'\n'


def test_memoriam_config_domain(runner):
    assert runner.invoke(config, ['--domain']).output == Path('memoriam/data/domain_schema.yml').resolve().read_text()+'\n'


def test_memoriam_config_index(runner):
    assert runner.invoke(config, ['--index']).output == Path('memoriam/data/index_config.yml').resolve().read_text()+'\n'


def test_memoriam_config_search(runner):
    assert runner.invoke(config, ['--search']).output == Path('memoriam/data/search_config.yml').resolve().read_text()+'\n'


def test_memoriam_config_service(runner):
    assert runner.invoke(config, ['--service']).output == Path('memoriam/data/service_config.yml').resolve().read_text()+'\n'


def test_memoriam_config_logging(runner):
    assert runner.invoke(config, ['--logging']).output == Path('memoriam/data/logging_config.yml').resolve().read_text()+'\n'


def test_memoriam_config_help(runner):
    assert runner.invoke(config, ['']).output == """Usage: config [OPTIONS]\nTry 'config --help' for help.\n\nError: Got unexpected extra argument ()\n"""


def test_memoriam_config_help_when_not_correct_argument(runner):
    assert runner.invoke(config, ['wrong argument']).output == """Usage: config [OPTIONS]\nTry 'config --help' for help.\n\nError: Got unexpected extra argument (wrong argument)\n"""
