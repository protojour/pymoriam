import time
import logging

from sanic.response import empty
from sanic.exceptions import SanicException
from sanic.compat import Header

from memoriam.utils import scrub_headers
from memoriam.config import (
    NO_AUTH, NO_AC, AUTHLY_SERVICENAME
)
from memoriam.authly import AuthlyClient, AUTHLY_URL


logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')


class AccessControlGuard(AuthlyClient):
    """Access control guard extension"""

    def __init__(self, app):
        super().__init__(app)

        if not NO_AC:
            app.add_route(self.resolve, '/system/api/resolve')

    def access_middleware(self, request):
        """"Middleware" for validating against Authly access policies"""
        start = time.perf_counter() * 1000

        # bypass – safe only if requests are routed through Gateway
        if request.headers.get('x-authly-entity-id') == AUTHLY_SERVICENAME:
            return

        resource = request.headers.get('x-authly-resource', '')
        action = request.headers.get('x-authly-action', '')
        eid = request.headers.get('x-authly-eid', '')
        name = request.headers.get('x-authly-entity-id')
        type_ = request.headers.get('x-authly-entity-type')

        response = self.service_request('post', f'{AUTHLY_URL}/service/resource/{resource}/resolve/{eid}/{action}')

        logger.debug(f'{type_} {name} attempting "{action}" on {resource}... {response.json()[0]}')

        log_perf.debug(f'Access resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        if response.json()[0] == 'ALLOW':
            return
        else:
            raise SanicException('Unauthorized', status_code=401)

    def authorize(self, request, resource='', action=''):
        """Authorize action on resource for given request against self"""
        if NO_AUTH or NO_AC:
            return

        headers = request.headers.copy()
        request.headers = Header({
            **scrub_headers(request.headers),
            'x-authly-resource': resource,
            'x-authly-action': action,
        })
        self.access_middleware(request)

        request.headers = headers

    async def resolve(self, request):
        """Allows explicitly calling self.access_middleware()"""
        self.access_middleware(request)

        return empty(200)
