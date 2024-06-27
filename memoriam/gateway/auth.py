import logging
import re
import time

import httpx

from sanic.exceptions import SanicException, Unauthorized

from memoriam.config import NO_AUTH, CA_FILE, AUTHLY_HOST, AUTHLY_PORT
from memoriam.utils import scrub_headers


logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')

AUTHLY_URL = f'https://{AUTHLY_HOST}:{AUTHLY_PORT}'

AUTH_ALLOWLIST = [
    r'/',
    r'/health',
    r'/onto',
    r'/onto/.*',
    r'/docs',
    r'/docs/.*',
    r'/favicon\.(ico|png)',
    r'/static/.*',
    r'/\w+?/api',
    r'/\w+?/api/openapi\.json',
    r'/authly/api/health',
    r'/authly/api/auth/authenticate',
    r'/authly/api/auth/authorities',
    r'/authly/api/auth/session',
]

AUTH_DENYLIST = [
    r'/authly/api/docs',
    r'/authly/api/docs/.*',
]


def get_session_middleware(auth_url):
    """Get session middleware for auth service"""

    async def session_middleware(request):
        """Middleware checking auth credentials with Authly.
           Returns an early 401 on invalid credentials,
           and appends request headers from valid session"""
        if NO_AUTH:
            return

        if any([re.fullmatch(pattern, request.path) for pattern in AUTH_DENYLIST]):
            raise Unauthorized('No authorization header or session-cookie', 401)

        if any([re.fullmatch(pattern, request.path) for pattern in AUTH_ALLOWLIST]):
            return

        if ('session-cookie' not in request.cookies and
            'authorization' not in request.headers):
            raise Unauthorized('No authorization header or session-cookie', 401)

        pre_proxy = time.perf_counter() * 1000

        async with httpx.AsyncClient(http2=True, verify=CA_FILE) as httpx_client:
            try:
                proxy_response = await httpx_client.get(
                    f'{auth_url}/auth/session',
                    headers=scrub_headers(request.headers),
                    cookies=dict(request.cookies)
                )
            except httpx.RequestError as e:
                raise SanicException(f'Error while requesting {e.request.url}: {e}') from None

            log_perf.debug(f'Authly response time: {(time.perf_counter() * 1000 - pre_proxy):.2f} ms')

            if proxy_response.status_code != 200:
                raise Unauthorized('Invalid or outdated session', 401)

        profile = proxy_response.json().get('profile', {})
        request.headers['x-authly-eid'] = str(profile.get('entityID', ''))
        request.headers['x-authly-entity-type'] = profile.get('entityType', '')

        if request.headers['x-authly-entity-type'] == 'Service':
            request.headers['x-authly-entity-id'] = profile.get('serviceName', '')

        elif request.headers['x-authly-entity-type'] == 'User':
            request.headers['x-authly-entity-id'] = profile.get('username', '')

    return session_middleware
