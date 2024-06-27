import logging
import time
from base64 import b64encode
from itertools import cycle

import httpx

from sanic.exceptions import SanicException, Unauthorized
from sanic.response import raw
from memoriam.config import (
    ARANGO_HOST, ARANGO_HOSTS, ARANGO_PORT, ARANGO_SCHEME,
    ARANGO_USERNAME, ARANGO_PASSWORD,
    CA_FILE, REQUEST_TIMEOUT
)
from memoriam.utils import scrub_headers


logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')


class ArangoProxy:
    """Extension to initialize ArangoDB and set up
       proxy requests to ArangoDB API, allowing access control"""

    def __init__(self, app):
        self.app = app
        self.app.ctx.arango_proxy = self

        self.hosts = (
            ARANGO_HOSTS.split(',')
            if ARANGO_HOSTS else
            [f'{ARANGO_SCHEME}://{ARANGO_HOST}:{ARANGO_PORT}']
        )
        self.host_iterator = self.get_host_iterator()

        app.register_middleware(self.arango_auth_middleware, 'request')

        methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        app.add_route(self.arango_proxy, '/_db/<path:path>', methods=methods)
        app.add_route(self.arango_proxy, '/_api/<path:path>', methods=methods)
        app.add_route(self.arango_proxy, '/_admin/<path:path>', methods=methods)

    def get_host_iterator(self):
        """Return an iterator that cycles through the hosts in self.hosts"""
        for host in cycle(self.hosts):
            yield host

    async def arango_auth_middleware(self, request):
        """Request middleware storing Authly credentials and replacing with ArangoDB authentication"""
        if request.path.split('/')[1] in ('_db', '_api', '_admin'):
            if ARANGO_USERNAME and ARANGO_PASSWORD:
                if request.headers.get('x-authly-entity-type') != 'Service':
                    raise Unauthorized('User access to ArangoDB not allowed', 401)

                auth_header = request.headers.pop('authorization', '')
                request.headers['x-authly-authorization'] = auth_header if 'Bearer' in auth_header else ''
                request.headers['x-authly-cookie'] = request.cookies.pop('session-cookie', '')

                auth = f'{ARANGO_USERNAME}:{ARANGO_PASSWORD}'.encode('ascii')
                base64_auth = b64encode(auth).decode('ascii')
                request.headers['authorization'] = f'Basic {base64_auth}'

    async def arango_proxy(self, request, path):
        """Reverse proxy for requests to ArangoDB"""
        host = next(self.host_iterator)

        request_headers = dict(request.headers)
        request_headers.pop('host', None)

        pre_proxy = time.perf_counter() * 1000

        try:
            proxy_response = httpx.request(
                method=request.method,
                url=(host + request.path + (f'?{request.query_string}' if request.query_string else '')),
                content=request.body,
                headers=request_headers,
                timeout=REQUEST_TIMEOUT,
                verify=CA_FILE
            )
        except httpx.RequestError as e:
            raise SanicException(f'Error while requesting {e.request.url}: {e}') from None

        log_perf.debug(f'ArangoDB reverse proxy response time: {(time.perf_counter() * 1000 - pre_proxy):.2f} ms')

        return raw(
            body=proxy_response.content,
            status=proxy_response.status_code,
            headers=dict(scrub_headers(proxy_response.headers))
        )
