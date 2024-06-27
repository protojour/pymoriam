import logging

from pathlib import Path

import click
import jsonschema_rs as jsrs
from sanic import Sanic
from sanic.worker.loader import AppLoader
from sanic.worker.manager import WorkerManager

import memoriam.config as conf
from memoriam.logs import init_logging_config
from memoriam.utils import get_version, load_yaml
from memoriam.constants import RELOAD_DIRS
from memoriam.gateway.app import init_app as init_gateway
from memoriam.domain.app import init_app as init_domain
from memoriam.storage.app import init_app as init_storage

WorkerManager.THRESHOLD = 600

logging_config = load_yaml(path=conf.LOGGING_CONFIG_PATH)
validation_schema = load_yaml(path=Path(conf.ROOT_PATH, 'data', 'logging_config_validation_schema.yml').resolve())
jsrs.JSONSchema(validation_schema).validate(logging_config)
init_logging_config(logging_config)

logger = logging.getLogger('memoriam')
version = get_version()


class NaturalOrderGroup(click.Group):
    """Group to show commands in their specified order"""

    def list_commands(self, ctx):
        return self.commands.keys()


@click.group(cls=NaturalOrderGroup)
def memoriam():
    """Open analytical data warehouse platform"""
    pass


@memoriam.command()
def gateway():
    """Run Memoriam in Gateway mode"""
    logger.info(f'🧠 Memoriam v{version} starting in Gateway mode')

    loader = AppLoader(factory=init_gateway)
    loader.load().prepare(
        host='0.0.0.0',
        motd=False,
        port=conf.GATEWAY_PORT,
        ssl=conf.TLS_CONFIG,
        debug=conf.DEBUG,
        workers=conf.GATEWAY_WORKERS,
        backlog=conf.BACKLOG,
        auto_reload=conf.AUTO_RELOAD,
        auto_tls=conf.AUTO_TLS,
        reload_dir=RELOAD_DIRS,
    )
    Sanic.serve(app_loader=loader)


@memoriam.command()
def domain():
    """Run Memoriam in Domain mode"""
    logger.info(f'🧠 Memoriam v{version} starting in Domain mode')

    loader = AppLoader(factory=init_domain)
    loader.load().prepare(
        host='0.0.0.0',
        motd=False,
        port=conf.DOMAIN_PORT,
        ssl=conf.TLS_CONFIG,
        debug=conf.DEBUG,
        workers=conf.DOMAIN_WORKERS,
        backlog=conf.BACKLOG,
        auto_reload=conf.AUTO_RELOAD,
        auto_tls=conf.AUTO_TLS,
        reload_dir=RELOAD_DIRS,
    )
    Sanic.serve(app_loader=loader)


@memoriam.command()
def storage():
    """Run Memoriam in Storage mode"""
    logger.info(f'🧠 Memoriam v{version} starting in Storage mode')

    loader = AppLoader(factory=init_storage)
    loader.load().prepare(
        host='0.0.0.0',
        motd=False,
        port=conf.STORAGE_PORT,
        ssl=conf.TLS_CONFIG,
        debug=conf.DEBUG,
        workers=conf.STORAGE_WORKERS,
        backlog=conf.BACKLOG,
        auto_reload=conf.AUTO_RELOAD,
        auto_tls=conf.AUTO_TLS,
        reload_dir=RELOAD_DIRS,
    )
    Sanic.serve(app_loader=loader)


@memoriam.command(no_args_is_help=True)
@click.option('--db', is_flag=True, help='Export template database schema in YAML format')
@click.option('--domain', is_flag=True, help='Export template domain schema in YAML format')
@click.option('--index', is_flag=True, help='Export template index config in YAML format')
@click.option('--search', is_flag=True, help='Export template search config in YAML format')
@click.option('--service', is_flag=True, help='Export template service config in YAML format')
@click.option('--logging', is_flag=True, help='Export template logging config in YAML format')
@click.option('--authly', is_flag=True, help='Export template Authly operations script in YAML format')
def config(db, domain, index, search, service, logging, authly):
    """Export template configs"""
    if db:
        click.echo(Path('memoriam/data/db_schema.yml').resolve().read_text())
    if domain:
        click.echo(Path('memoriam/data/domain_schema.yml').resolve().read_text())
    if index:
        click.echo(Path('memoriam/data/index_config.yml').resolve().read_text())
    if search:
        click.echo(Path('memoriam/data/search_config.yml').resolve().read_text())
    if service:
        click.echo(Path('memoriam/data/service_config.yml').resolve().read_text())
    if logging:
        click.echo(Path('memoriam/data/logging_config.yml').resolve().read_text())
    if authly:
        click.echo(Path('memoriam/data/authly_operations.yml').resolve().read_text())
