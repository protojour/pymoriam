import time
import logging
from pathlib import Path

import httpx
import jsonschema_rs as jsrs
from caseconverter import snakecase

from sanic.exceptions import SanicException, InvalidUsage, NotFound
from sanic.response import json, empty, raw

from memoriam.config import CA_FILE, DOMAIN_WORKERS, ROOT_PATH, SERVICE_CONFIG_PATH, REQUEST_TIMEOUT
from memoriam.proxy import ws_connection
from memoriam.utils import load_yaml, scrub_headers


logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')


class ServiceInterface:
    """This Sanic extension exposes service registration, data access and client communication
       interfaces to the Memoriam service layer"""

    def __init__(self, app):
        self.app = app

        if DOMAIN_WORKERS > 1:
            app.register_listener(self.init_services, 'main_process_start')
        else:
            app.register_listener(self.init_services, 'before_server_start')

        app.add_websocket_route(service_ws_proxy, '/system/api/ws/service/<service_name>/<path:path>')

    async def init_services(self, app):
        """Initialize services from YAML config, store in cache"""
        if not SERVICE_CONFIG_PATH:
            return

        validation_schema = load_yaml(path=Path(ROOT_PATH, 'data', 'service_config_validation_schema.yml').resolve())
        service_config = load_yaml(path=SERVICE_CONFIG_PATH)
        jsrs.JSONSchema(validation_schema).validate(service_config)

        service_info = {}
        service_apis = {}
        service_rpcs = {}

        for service_name, service_spec in service_config.get('services', {}).items():

            name = service_spec.get('name', service_name)
            host = service_spec.get('host', '')
            health = service_spec.get('health', '')
            api = service_spec.get('api', '')
            rpc = service_spec.get('rpc', {})

            service_info[snakecase(service_name)] = {**service_spec, 'name': name}
            logger.info(f'Service {name} registered')

            if host and api:
                service_apis[snakecase(service_name)] = host
                service_info[snakecase(service_name)]['api'] = host + api
                logger.info(f'Service {name} API registered')

            if host and health:
                service_info[snakecase(service_name)]['health'] = host + health
                logger.info(f'Service {name} health check registered')

            service_rpcs = service_rpcs or {}
            service_rpcs = self.init_rpc(name, service_rpcs, host, rpc)

        await app.ctx.cache.set('service_info', service_info)
        await app.ctx.cache.set('service_apis', service_apis)
        await app.ctx.cache.set('service_rpcs', service_rpcs)

    @staticmethod
    def init_rpc(service_name, service_rpcs, host, rpc):
        for class_name, class_spec in rpc.items():
            relations = class_spec.pop('relations', {})
            for op, op_spec in class_spec.items():
                for pos in ('pre', 'post'):
                    path = op_spec.get(pos)
                    if path:
                        signal = f'{pos}_{op}_obj_{class_name}'
                        if signal not in service_rpcs:
                            service_rpcs[signal] = []

                        url = host + path
                        if url not in service_rpcs[signal]:
                            service_rpcs[signal].append(url)

                        logger.info(f'Service {service_name} {signal} RPC listener registered')

            for rel_name, rel_spec in relations.items():
                for op, op_spec in rel_spec.items():
                    for pos in ('pre', 'post'):
                        path = op_spec.get(pos)
                        if path:
                            signal = f'{pos}_{op}_rel_{class_name}_{rel_name}'
                            if signal not in service_rpcs:
                                service_rpcs[signal] = []

                            url = host + path
                            if url not in service_rpcs[signal]:
                                service_rpcs[signal].append(url)

                            logger.info(f'Service {service_name} {signal} RPC listener registered')

            if relations:
                class_spec['relations'] = relations

        return service_rpcs


async def service_status(request):
    """Lists connected services and their status"""
    request.app.ctx.authorize(request, 'service', 'status')

    cache = request.app.ctx.cache
    service_info = await cache.get('service_info', {})

    status = 200

    for _, service in service_info.items():
        name = service.get('name')
        health = service.get('health')

        if health:
            logger.debug(f'Health checking service {name}')

            async with httpx.AsyncClient(http2=True, verify=CA_FILE, timeout=REQUEST_TIMEOUT) as client:
                try:
                    response = await client.get(
                        url=health,
                        headers=dict(request.headers),
                        follow_redirects=True
                    )

                except httpx.RequestError as e:
                    status = 500
                    service['status_code'] = 500
                    service['status'] = str(e)

                else:
                    service['status_code'] = response.status_code
                    service['status'] = response.text

                    if response.status_code != 200:
                        status = 500
                        service['status'] = response.reason_phrase

                    if 'application/json' in response.headers.get('content-type', ''):
                        service['status'] = response.json()

    return json(service_info, status)


async def register_service(request):
    """Handler for registering services"""
    request.app.ctx.authorize(request, 'service', 'register')

    data = request.json

    name = data.get('name')
    info = data.get('info')
    host = data.get('host', '')
    health = data.get('health', '')
    api = data.get('api', '')
    rpc = data.get('rpc', {})

    if not (name and info):
        error = 'name and info are required parameters'
        logger.debug(error)
        raise InvalidUsage(error, 400)

    cache = request.app.ctx.cache
    service_info = await cache.get('service_info', {})
    service_apis = await cache.get('service_apis', {})
    service_rpcs = await cache.get('service_rpcs', {})

    service_info[snakecase(name)] = data
    logger.info(f'Service {name} registered')

    if host and api:
        service_apis[snakecase(name)] = host
        service_info[snakecase(name)]['api'] = host + api
        logger.info(f'Service {name} API registered')

    if host and health:
        service_info[snakecase(name)]['health'] = host + health
        logger.info(f'Service {name} health check registered')

    service_rpcs = ServiceInterface.init_rpc(name, service_rpcs, host, rpc)

    await cache.set('service_info', service_info)
    await cache.set('service_apis', service_apis)
    await cache.set('service_rpcs', service_rpcs)

    return json({}, 201)


async def unregister_service(request, service_name):
    """Handler for unregistering services"""
    request.app.ctx.authorize(request, 'service', 'unregister')

    cache = request.app.ctx.cache
    service_info = await cache.get('service_info', {})
    service_apis = await cache.get('service_apis', {})

    if service_name not in service_info:
        error = f'Service {service_name} is not registered'
        logger.debug(error)
        raise NotFound(error, 404)

    name = service_info[service_name].get('name')

    del service_info[service_name]
    await cache.set('service_info', service_info)
    logger.info(f'Service {name} unregistered')

    if service_name in service_apis:
        del service_apis[service_name]
        await cache.set('service_apis', service_apis)
        logger.info(f'Service {name} API unregistered')

    return empty()


async def service_api_proxy(request, service_name, path):
    """Reverse proxy for service APIs"""
    request.app.ctx.authorize(request, 'service', 'proxy')

    cache = request.app.ctx.cache
    service_apis = await cache.get('service_apis', {})
    host = service_apis.get(service_name)

    if not host:
        error = f'Service {service_name} API is not registered'
        logger.debug(error)
        raise NotFound(error, 404)

    pre_proxy = time.perf_counter() * 1000

    async with httpx.AsyncClient(verify=CA_FILE, timeout=REQUEST_TIMEOUT) as client:
        try:
            url = f'{host}/{path}' + (f'?{request.query_string}' if request.query_string else '')
            proxy_response = await client.request(
                method=request.method,
                url=url,
                content=request.body,
                headers=dict(request.headers)
            )
        except httpx.RequestError as e:
            raise SanicException(f'Error while requesting {e.request.url}: {e}') from None

    log_perf.debug(f'Service API proxy response time: {(time.perf_counter() * 1000 - pre_proxy):.2f} ms')

    return raw(
        body=proxy_response.content,
        status=proxy_response.status_code,
        headers=dict(scrub_headers(proxy_response.headers))
    )


async def service_ws_proxy(request, ws, service_name, path):
    """Reverse proxy for service API websockets"""
    cache = request.app.ctx.cache
    service_apis = await cache.get('service_apis', {})
    host = service_apis.get(service_name)

    if not host:
        error = f'Service {service_name} API is not registered'
        logger.debug(error)
        raise NotFound(error, 404)

    url = f'{host}/{path}?{request.query_string}'

    await ws_connection(ws, url)
