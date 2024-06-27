import logging

import sentry_sdk
from redis.asyncio import Redis
from sentry_sdk.integrations.sanic import SanicIntegration
from sanic import Sanic, Blueprint
from sanic.response import json
from cashews import Cache

import memoriam.config
from memoriam.config import (
    SENTRY_DSN, CA_FILE, ARANGO_DOMAIN_SCHEMA_PATH,
    DOMAIN_HOST, MINIO_HOST, CACHE_CONFIG, ARANGO_DEFAULT_LIMIT,
    REDIS_HOST, REDIS_PORT, REDIS_TLS, REDIS_DATABASE, REDIS_PASSWORD
)
from memoriam.authly import AuthlyClient
from memoriam.openapi import OpenAPI
from memoriam.domain.audit import AuditLog
from memoriam.domain.domain_init import DomainInit
from memoriam.domain.search import ArangoSearch
from memoriam.domain.rest import RESTResolverEngine
from memoriam.domain.graphql import GraphQLResolverEngine
from memoriam.domain.services import ServiceInterface
from memoriam.utils import LoggingErrorHandler, load_yaml
from memoriam.domain.jinja import env as jinja_env


logger = logging.getLogger('memoriam')
api = Blueprint('api')


def init_app():
    """Initialize the domain app"""
    if SENTRY_DSN:
        # pylint: disable=E0110
        sentry_sdk.init(
           dsn=SENTRY_DSN,
           ca_certs=CA_FILE if isinstance(CA_FILE, str) else None,
           server_name=DOMAIN_HOST,
           integrations=[SanicIntegration()]
        )

    if 'memoriam-domain' in Sanic._app_registry:
        app = Sanic.get_app('memoriam-domain')
    else:
        app = Sanic('memoriam-domain', configure_logging=False)

    app.update_config(memoriam.config)
    app.config.AUTO_EXTEND = False
    app.error_handler = LoggingErrorHandler()
    app.blueprint(api)

    app.ctx.cache = Cache(name='memoriam')
    app.ctx.cache.default_prefix = 'memoriam'
    app.ctx.cache.setup(**CACHE_CONFIG)

    app.ctx.redis = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DATABASE,
        password=REDIS_PASSWORD,
        ssl=REDIS_TLS
    )

    app.register_listener(clear_caches, 'main_process_start')

    if hasattr(app.ctx, 'init'):
        return app

    app.ctx.init = True

    openapi_template = jinja_env.get_template('openapi_spec_system.yml')
    yaml_spec = openapi_template.render(
        include_storage_api=bool(MINIO_HOST),
        default_limit=ARANGO_DEFAULT_LIMIT
    )
    dict_spec = load_yaml(yaml_spec)

    system_api = OpenAPI(
        app=app,
        namespace='system',
        spec=dict_spec,
        schema_path=ARANGO_DOMAIN_SCHEMA_PATH,
        base_url='/system/api'
    )

    AuditLog(app, system_api)
    DomainInit(app)
    AuthlyClient(app)
    ServiceInterface(app)

    RESTResolverEngine(app)
    GraphQLResolverEngine(app)
    ArangoSearch(app)

    return app


async def clear_caches(app):
    await app.ctx.redis.delete('memoriam_domain_cache')
    await app.ctx.redis.delete('memoriam_graphql_schemas')
    await app.ctx.redis.delete('memoriam_rest_schemas')


@api.get('/health')
async def health(request):
    return json('Ok')
