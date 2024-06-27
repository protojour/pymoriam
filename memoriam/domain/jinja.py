from pathlib import Path

import yaml
from caseconverter import pascalcase, snakecase
from jinja2 import Environment, FileSystemLoader

from memoriam.config import ROOT_PATH
from memoriam.utils import Dumper


templates_path = Path(ROOT_PATH, 'templates').resolve()

env = Environment(
    loader=FileSystemLoader(templates_path),
    trim_blocks=True,
    lstrip_blocks=True
)


def get_type(value):
    """Get OpenAPI type for constants"""
    if isinstance(value, str):
        return 'string'
    if isinstance(value, float):
        return 'number'
    if isinstance(value, int):
        return 'integer'
    if isinstance(value, bool):
        return 'boolean'


def yaml_dump(value):
    """Dump a value (str, int, list, dict etc.) to a YAML structure"""
    return yaml.dump(value, sort_keys=False, Dumper=Dumper)[:-1]


env.filters['pascalcase'] = pascalcase
env.filters['snakecase'] = snakecase
env.filters['yaml'] = yaml_dump
env.filters['get_type'] = get_type
