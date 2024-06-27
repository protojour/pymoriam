import logging

import httpx
import typing
import ujson
import sentry_sdk

from redis.asyncio import Redis

from sentry_sdk.integrations.sanic import SanicIntegration
from sanic import Sanic, Blueprint
from sanic.models.handler_types import RouteHandler
from sanic.response import redirect, file, json, empty
from sanic_ext import Extend
from sanic_ext.extensions.http.extension import HTTPExtension

import memoriam.config
from memoriam.config import (
    SENTRY_DSN, HOST_DOCS, NO_AUTH, CA_FILE, REQUEST_TIMEOUT,
    GATEWAY_HOST, MINIO_HOST,
    DOMAIN_HOST, DOMAIN_PORT, DOMAIN_SCHEME,
    STORAGE_HOST, STORAGE_PORT, STORAGE_SCHEME,
    AUTHLY_SERVICENAME, AUTHLY_HOST, AUTHLY_PORT,
    REDIS_HOST, REDIS_PORT, REDIS_DATABASE, REDIS_PASSWORD, REDIS_TLS
)
from memoriam.authly import AuthlyClient
from memoriam.compress import Compress
from memoriam.proxy import get_reverse_proxy, get_ws_reverse_proxy
from memoriam.gateway.auth import get_session_middleware
from memoriam.gateway.onto import get_service, get_logo, post_logo
from memoriam.utils import LoggingErrorHandler


logger = logging.getLogger('memoriam')
api = Blueprint('gateway')


def init_app():
    """Initialize the gateway app"""
    if SENTRY_DSN:
        # pylint: disable=E0110
        sentry_sdk.init(
           dsn=SENTRY_DSN,
           ca_certs=CA_FILE if isinstance(CA_FILE, str) else None,
           server_name=GATEWAY_HOST,
           integrations=[SanicIntegration()]
        )

    if 'memoriam-gateway' in Sanic._app_registry:
        app = Sanic.get_app('memoriam-gateway')
    else:
        app = Sanic('memoriam-gateway', configure_logging=False)

    app.update_config(memoriam.config)
    app.config.AUTO_EXTEND = False
    app.error_handler = LoggingErrorHandler()
    app.blueprint(api)

    Extend(app, extensions=[HTTPExtension], built_in_extensions=False)
    Compress(app)

    app.ctx.redis = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DATABASE,
        password=REDIS_PASSWORD,
        ssl=REDIS_TLS
    )

    if hasattr(app.ctx, 'init'):
        return app

    app.ctx.init = True

    AuthlyClient(app)

    app.add_route(typing.cast(RouteHandler, lambda request: redirect('/onto')), '/')
    app.add_route(lambda request: file('./onto/index.html'), '/onto')
    app.static('/onto', './onto')
    app.register_middleware(onto_fallback, 'response')

    app.static('/favicon.ico', '/static/favicon.png')
    app.static('/favicon.png', '/static/favicon.png')
    app.static('/static', './static')

    if HOST_DOCS:
        app.add_route(typing.cast(RouteHandler, lambda request: redirect('/docs/index.html')), '/docs')
        app.static('/docs', './docs')
    else:
        app.add_route(typing.cast(RouteHandler, lambda request: empty(404)), '/docs')
        app.static('/docs/_static', './docs/_static')

    methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    domain_url = f'{DOMAIN_SCHEME}://{DOMAIN_HOST}:{DOMAIN_PORT}'
    app.add_websocket_route(get_ws_reverse_proxy(domain_url), '/system/api/ws/<path:path>')
    app.add_route(get_reverse_proxy(domain_url, 'Gateway'), '/<path:path>', methods=methods)

    storage_url = f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}'
    app.add_route(get_reverse_proxy(storage_url + '/system/api/storage', 'Gateway'), '/system/api/storage/<path:path>', methods=methods)
    app.add_route(get_reverse_proxy(storage_url + '/redis', 'Gateway'), '/redis/<path:path>', methods=methods)
    app.add_route(get_reverse_proxy(storage_url + '/minio', 'Gateway'), '/minio/<path:path>', methods=methods)
    app.add_route(get_reverse_proxy(storage_url + '/_db', 'Gateway'), '/_db/<path:path>', methods=methods)
    app.add_route(get_reverse_proxy(storage_url + '/_api', 'Gateway'), '/_api/<path:path>', methods=methods)
    app.add_route(get_reverse_proxy(storage_url + '/_admin', 'Gateway'), '/_admin/<path:path>', methods=methods)

    if NO_AUTH:
        app.add_route(typing.cast(RouteHandler, lambda request, path: empty(404)), '/authly/<path:path>', methods=methods)
    else:
        auth_url = f'https://{AUTHLY_HOST}:{AUTHLY_PORT}'
        app.add_route(get_reverse_proxy(auth_url, 'Authly'), '/authly/<path:path>', methods=methods)
        app.register_middleware(get_session_middleware(auth_url + '/api'), 'request')

        app.add_route(get_service, '/authly/api/service/service', ['GET'])
        app.add_route(get_logo, '/authly/api/service/service/<service_name>/logo', ['GET'])
        app.add_route(post_logo, '/authly/api/service/service/<service_name>/logo', ['POST'])

    return app


async def onto_fallback(request, response):
    """Handler giving a fallback for SvelteKit router and Sanic static files incompatibility"""
    if request.path == '/onto/' and response.status == 500:
        return await file('./onto/index.html')
    if request.path.startswith('/onto') and response.status == 404:
        return await file('./onto/index.html')


@api.get('/health')
async def health(request):
    """Healthcheck endpoint collecting health info from base service mesh"""
    health_checks = {
        'Gateway': {
            'status_code': 200,
        },
        'Domain': {
            'url': f'{DOMAIN_SCHEME}://{DOMAIN_HOST}:{DOMAIN_PORT}/health',
        },
        'Storage': {
            'url': f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}/health',
        },
        'Services': {
            'url': f'{DOMAIN_SCHEME}://{DOMAIN_HOST}:{DOMAIN_PORT}/system/api/service',
        },
        'Authly': {
            'url': f'https://{AUTHLY_HOST}:{AUTHLY_PORT}/api/health',
        },
        'ArangoDB': {
            'url': f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}/_admin/status',
        },
        'Redis': {
            'url': f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}/redis/health',
        },
    }

    if MINIO_HOST:
        health_checks['Minio'] = {
            'url': f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}/minio/health',
        }

    status = 200
    headers = dict(request.headers)
    headers['accept'] = 'application/json'
    headers['x-authly-entity-id'] = AUTHLY_SERVICENAME
    headers['x-authly-entity-type'] = 'Service'

    for key, spec in health_checks.items():

        logger.debug(f'Health checking {key}')

        async with httpx.AsyncClient(http2=True, verify=CA_FILE, timeout=REQUEST_TIMEOUT) as client:

            url = spec.get('url')
            if not url:
                continue

            try:
                response = await client.get(
                    url=url,
                    headers=headers,
                    follow_redirects=True
                )
            except httpx.RequestError as e:
                status = 500
                health_checks[key]['status_code'] = 500
                health_checks[key]['status'] = {'error': str(e)}
            else:
                health_checks[key]['status_code'] = response.status_code

                if response.status_code != 200:
                    status = 500
                    logger.debug(response.text)
                    health_checks[key]['status'] = {'error': response.reason_phrase}

                if key == 'ArangoDB':
                    health_checks[key]['status'] = ujson.loads(response.text)

                if 'application/json' in response.headers.get('content-type', ''):
                    health_checks[key]['status'] = response.json()

    return json(health_checks, status=status)
