import logging
from pathlib import Path

from redis.asyncio import Redis
import sentry_sdk

from minio import Minio
from sentry_sdk.integrations.sanic import SanicIntegration
from sanic import Sanic, Blueprint
from sanic.response import json
from sanic.exceptions import SanicException

import memoriam.config
from memoriam.config import (
    SENTRY_DSN, ROOT_PATH, STORAGE_HOST, CA_FILE,
    REDIS_HOST, REDIS_PORT, REDIS_TLS, REDIS_DATABASE, REDIS_PASSWORD,
    MINIO_HOST, MINIO_PORT, MINIO_TLS, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
)
from memoriam.openapi import OpenAPI
from memoriam.storage.access_control import AccessControlGuard
from memoriam.storage.arango_init import ArangoInit
from memoriam.storage.arango_proxy import ArangoProxy
from memoriam.utils import LoggingErrorHandler


logger = logging.getLogger('memoriam')
api = Blueprint('api')


def init_app():
    """Initialize the storage app"""
    if SENTRY_DSN:
        # pylint: disable=E0110
        sentry_sdk.init(
           dsn=SENTRY_DSN,
           ca_certs=CA_FILE if isinstance(CA_FILE, str) else None,
           server_name=STORAGE_HOST,
           integrations=[SanicIntegration()]
        )

    if 'memoriam-storage' in Sanic._app_registry:
        app = Sanic.get_app('memoriam-storage')
    else:
        app = Sanic('memoriam-storage', configure_logging=False)

    app.update_config(memoriam.config)
    app.config.AUTO_EXTEND = False
    app.error_handler = LoggingErrorHandler()
    app.blueprint(api)

    if hasattr(app.ctx, 'init'):
        return app

    app.ctx.init = True

    ArangoInit(app)
    AccessControlGuard(app)
    ArangoProxy(app)

    if MINIO_HOST:
        OpenAPI(
            app=app,
            namespace='system',
            spec_path=Path(ROOT_PATH, 'data', 'openapi_spec_storage.yml').resolve(),
            base_url='/system/api'
        )

    return app


@api.get('/health')
async def health(request):
    return json('Ok')


@api.get('/redis/health')
async def redis_health(request):
    """Health check endpoint for Redis"""
    redis = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DATABASE,
        password=REDIS_PASSWORD,
        ssl=REDIS_TLS
    )
    try:
        await redis.ping()
    except Exception as e:
        logger.exception(e)
        return json({'error': str(e)}, 500)
    finally:
        await redis.close()

    return json('Ok')


@api.get('/minio/health')
async def minio_health(request):
    """Health check endpoint for Minio"""
    if not MINIO_HOST:
        raise SanicException('Minio is not enabled', 404)

    minio = Minio(
        f'{MINIO_HOST}:{MINIO_PORT}',
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=MINIO_TLS
    )
    try:
        minio.list_buckets()
    except Exception as e:
        logger.exception(e)
        return json({'error': str(e)}, 500)

    return json('Ok')
