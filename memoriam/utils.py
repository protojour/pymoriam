import asyncio
import logging
import re

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from caseconverter import pascalcase
from graphql import Undefined
from sanic.exceptions import SanicException
from sanic.handlers import ErrorHandler
from sanic.compat import Header

import yaml

try:  # pragma: no cover
    from yaml import CSafeLoader as Loader, CSafeDumper as Dumper # noqa
except ImportError:
    from yaml import SafeLoader as Loader, SafeDumper as Dumper # noqa


logger = logging.getLogger('memoriam')
log_error = logging.getLogger('memoriam.error')


def trueish(value):
    """Return True if value is true-ish"""
    return value in (True, 'True', 'true', 'yes', 'on', '1', 1)


def iso8601_now():
    """Get current UTC timestamp in ISO8601 format (with Z as UTC indicator)"""
    return datetime.utcnow().isoformat() + 'Z'


def get_user_id(request):
    """Get user (entity) id added by session middleware from request"""
    return request.headers.get('x-authly-entity-id')


def scrub_headers(dirty_headers):
    """Scrub problematic headers before passing on in a new request or response"""
    headers = dict(dirty_headers)
    if 'transfer-encoding' in headers:
        del headers['transfer-encoding']
    # content-length is added automatically
    if 'content-length' in headers:
        del headers['content-length']
    return Header(headers)


def load_raw(path):
    """Load a raw file from path. Caches result."""
    return Path(path).resolve().read_text()


def load_yaml(data=None, path=None):
    """Safe load a YAML file from string or path. Caches result."""
    data = data or load_raw(path)
    return yaml.load(data, Loader=Loader)


def class_to_typename(obj):
    """Changes obj['_class'] to PascalCased obj['__typename'] for GraphQL type resolution.
       Will mutate obj!"""
    if obj and '_class' in obj:
        obj['__typename'] = pascalcase(obj.pop('_class'))
    return obj


def validate_iso8601(value):
    """Validate a datetime string, returns Undefined (invalid) or value (valid)"""
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return Undefined
    return value


def get_version():
    """Extract Memoriam version string from the current pyproject.toml file"""
    pyproject = Path(__file__, '..', '..', 'pyproject.toml').resolve().read_text()
    match = re.search(r'version = "(.*?)"', pyproject)
    return match.group(1) if match else ''


def clean_str(obj):
    """Recursive clean string representation of simple Python types"""
    if obj is None:
        return ''
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return ' '.join([clean_str(item) for item in obj])
    if isinstance(obj, dict):
        return ' '.join([clean_str(value) for value in obj.values()])

    # int, float, bool etc.
    return obj


def task_handler(task):
    """Properly handles exceptions in asyncio tasks"""
    try:
        task.result()
    except asyncio.CancelledError:
        pass  # not an error
    except Exception as e:
        raise SanicException(str(e)) from None


class LoggingErrorHandler(ErrorHandler):
    """Sanic ErrorHandler that logs exceptions and 5xx errors before returning"""
    def default(self, request, exception):
        """Overridden default handler"""
        if hasattr(exception, 'status_code'):
            if exception.status_code >= 500:
                log_error.exception(exception)
        else:
            log_error.exception(exception)

        return super().default(request, exception)


@dataclass
class Request:
    """Simplified Request dataclass for calling request handlers internally"""
    json: dict
    app: object
