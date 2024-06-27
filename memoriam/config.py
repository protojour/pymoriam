import os
from pathlib import Path

from memoriam.utils import trueish


DEBUG = trueish(os.getenv('DEBUG', False))
AUTO_TLS = trueish(os.getenv('AUTO_TLS', False))
AUTO_RELOAD = trueish(os.getenv('AUTO_RELOAD', False))
HOST_DOCS = trueish(os.getenv('HOST_DOCS', False))
NO_AUTH = trueish(os.getenv('NO_AUTH', False))
NO_AC = trueish(os.getenv('NO_AC', False))
NO_DELETE = trueish(os.getenv('NO_DELETE', False))
ACCESS_LOG = trueish(os.getenv('ACCESS_LOG', False))
AUDIT_LOG = trueish(os.getenv('AUDIT_LOG', False))
AUDIT_LOG_DB = trueish(os.getenv('AUDIT_LOG_DB', False))
AUDIT_VERSIONING = trueish(os.getenv('AUDIT_VERSIONING', False))
AQL_LOG = trueish(os.getenv('AQL_LOG', False))
PERF_LOG = trueish(os.getenv('PERF_LOG', False))
ERROR_LOG = trueish(os.getenv('ERROR_LOG', True))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')
INIT_DB = trueish(os.getenv('INIT_DB', True))
INIT_SEARCH = trueish(os.getenv('INIT_SEARCH', True))
UPDATE_SEARCH = trueish(os.getenv('UPDATE_SEARCH', False))
RELOAD_SCHEMAS = trueish(os.getenv('RELOAD_SCHEMAS', False))

CERT_FILE = os.getenv('CERT_FILE')
KEY_FILE = os.getenv('KEY_FILE')
CA_FILE = os.getenv('CA_FILE', True) or False
TLS_CONFIG = {
    'cert': CERT_FILE,
    'key': KEY_FILE,
    # TODO: these are hacks for 22.9,
    # report or replace by path or SSLContext
    'creator': 'mkcert',
    'localhost': 'localhost',
} if (CERT_FILE and KEY_FILE) else None

DEPRECATION_FILTER = 'ignore'
FALLBACK_ERROR_FORMAT = 'json'
NOISY_EXCEPTIONS = DEBUG
KEYPATH_SEPARATOR = os.getenv('KEYPATH_SEPARATOR', '||')

ROOT_PATH = Path(__file__, '..').resolve()

GATEWAY_HOST = os.getenv('GATEWAY_HOST', 'memoriam-gateway')
GATEWAY_PORT = int(os.getenv('GATEWAY_PORT', 5001))
GATEWAY_WORKERS = int(os.getenv('GATEWAY_WORKERS', 1))
GATEWAY_TLS = trueish(os.getenv('GATEWAY_TLS', False))
GATEWAY_SCHEME = 'https' if GATEWAY_TLS else 'http'

DOMAIN_HOST = os.getenv('DOMAIN_HOST', 'memoriam-domain')
DOMAIN_PORT = int(os.getenv('DOMAIN_PORT', 5002))
DOMAIN_WORKERS = int(os.getenv('DOMAIN_WORKERS', 1))
DOMAIN_TLS = trueish(os.getenv('DOMAIN_TLS', False))
DOMAIN_SCHEME = 'https' if DOMAIN_TLS else 'http'

STORAGE_HOST = os.getenv('STORAGE_HOST', 'memoriam-storage')
STORAGE_PORT = int(os.getenv('STORAGE_PORT', 5003))
STORAGE_WORKERS = int(os.getenv('STORAGE_WORKERS', 1))
STORAGE_TLS = trueish(os.getenv('STORAGE_TLS', False))
STORAGE_SCHEME = 'https' if STORAGE_TLS else 'http'

AUTHLY_HOST = os.getenv('AUTHLY_HOST', 'authly')
AUTHLY_PORT = int(os.getenv('AUTHLY_PORT', 5004))
AUTHLY_SERVICENAME = os.getenv('AUTHLY_SERVICENAME', '')
AUTHLY_SERVICESECRET = os.getenv('AUTHLY_SERVICESECRET', '')

ARANGO_HOST = os.getenv('ARANGO_HOST', 'arangodb')
ARANGO_PORT = int(os.getenv('ARANGO_PORT', 8529))
ARANGO_HOSTS = os.getenv('ARANGO_HOSTS')
ARANGO_TLS = trueish(os.getenv('ARANGO_TLS', False))
ARANGO_SCHEME = 'https' if ARANGO_TLS else 'http'
ARANGO_ROOT_USERNAME = os.getenv('ARANGO_ROOT_USERNAME', '')
ARANGO_ROOT_PASSWORD = os.getenv('ARANGO_ROOT_PASSWORD', '')
ARANGO_USERNAME = os.getenv('ARANGO_USERNAME', '')
ARANGO_PASSWORD = os.getenv('ARANGO_PASSWORD', '')
ARANGO_DB_NAME = os.getenv('ARANGO_DB_NAME', 'memoriam')
ARANGO_DOMAIN_DB_NAME = os.getenv('ARANGO_DOMAIN_DB_NAME', 'memoriam')
ARANGO_CONNECT_RETRIES = int(os.getenv('ARANGO_CONNECT_RETRIES', 60))
ARANGO_CONNECT_BACKOFF = float(os.getenv('ARANGO_CONNECT_BACKOFF', .5))
ARANGO_DEFAULT_LIMIT = int(os.getenv('ARANGO_DEFAULT_LIMIT', 100))

ARANGO_SCHEMA_PATH = os.getenv('ARANGO_SCHEMA_PATH', Path(ROOT_PATH, 'data', 'db_schema.yml'))
ARANGO_DOMAIN_SCHEMA_PATH = os.getenv('ARANGO_DOMAIN_SCHEMA_PATH', Path(ROOT_PATH, 'data', 'db_schema_domain.yml'))
DOMAIN_SCHEMA_PATH = os.getenv('DOMAIN_SCHEMA_PATH', Path(ROOT_PATH, 'data', 'domain_schema.yml'))
INDEX_CONFIG_PATH = os.getenv('INDEX_CONFIG_PATH', Path(ROOT_PATH, 'data', 'index_config.yml'))
SEARCH_CONFIG_PATH = os.getenv('SEARCH_CONFIG_PATH', Path(ROOT_PATH, 'data', 'search_config.yml'))
SERVICE_CONFIG_PATH = os.getenv('SERVICE_CONFIG_PATH', Path(ROOT_PATH, 'data', 'service_config.yml'))
LOGGING_CONFIG_PATH = os.getenv('LOGGING_CONFIG_PATH', Path(ROOT_PATH, 'data', 'logging_config.yml'))

MINIO_HOST = os.getenv('MINIO_HOST', 'minio')
MINIO_PORT = int(os.getenv('MINIO_PORT', 9000))
MINIO_TLS = trueish(os.getenv('MINIO_TLS', False))
MINIO_ROOT_USER = os.getenv('MINIO_ROOT_USER', None)
MINIO_ROOT_PASSWORD = os.getenv('MINIO_ROOT_PASSWORD', None)
MINIO_MAX_FILESIZE = int(os.getenv('MINIO_MAX_FILESIZE', 25 * 1024 * 1024))

REDIS_HOST = os.getenv('REDIS_HOST', 'valkey')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_TLS = trueish(os.getenv('REDIS_TLS', False))
REDIS_SCHEME = 'rediss' if REDIS_TLS else 'redis'
REDIS_DATABASE = int(os.getenv('REDIS_DATABASE', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

CACHE_CONFIG = {
    'settings_url': 'mem://',
    'prefix': 'memoriam'
}
if DOMAIN_WORKERS > 1:
    CACHE_CONFIG = {
        'settings_url': f'{REDIS_SCHEME}://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DATABASE}',
        'password': REDIS_PASSWORD,
        'prefix': 'memoriam'
    }

REQUEST_MAX_SIZE = int(os.getenv('REQUEST_MAX_SIZE', 20000000000))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 60))
RESPONSE_TIMEOUT = int(os.getenv('RESPONSE_TIMEOUT', 60))
KEEP_ALIVE_TIMEOUT = int(os.getenv('KEEPALIVE_TIMEOUT', 10))
WEBSOCKET_LOOP_TIMEOUT = float(os.getenv('WEBSOCKET_LOOP_TIMEOUT', 1))
WEBSOCKET_PING_INTERVAL = float(os.getenv('WEBSOCKET_PING_INTERVAL', 20))
WEBSOCKET_PING_TIMEOUT = float(os.getenv('WEBSOCKET_PING_TIMEOUT', 5))
BACKLOG = int(os.getenv('BACKLOG', 100))

SENTRY_DSN = os.getenv('SENTRY_DSN')

CORS_ALLOW_HEADERS = os.getenv('CORS_ALLOW_HEADERS', '*')
CORS_ALWAYS_SEND = trueish(os.getenv('CORS_ALWAYS_SEND', True))
CORS_AUTOMATIC_OPTIONS = trueish(os.getenv('CORS_AUTOMATIC_OPTIONS', True))
CORS_EXPOSE_HEADERS = os.getenv('CORS_EXPOSE_HEADERS', '')
CORS_MAX_AGE = os.getenv('CORS_MAX_AGE', '0')
CORS_METHODS = os.getenv('CORS_METHODS', '')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
CORS_SEND_WILDCARD = trueish(os.getenv('CORS_SEND_WILDCARD', False))
CORS_SUPPORTS_CREDENTIALS = trueish(os.getenv('CORS_SUPPORTS_CREDENTIALS', False))
CORS_VARY_HEADER = trueish(os.getenv('CORS_VARY_HEADER', True))

COMPRESS_LEVEL = max(0, min(int(os.getenv('COMPRESS_LEVEL', 6)), 9))
COMPRESS_MIN_SIZE = int(os.getenv('COMPRESS_MIN_SIZE', 256))
COMPRESS_MIMETYPES = [
    'text/html',
    'text/css',
    'image/png',
    'image/svg+xml',
    'application/json',
    'application/javascript',
    'application/octet-stream',
    'application/yaml'
]
