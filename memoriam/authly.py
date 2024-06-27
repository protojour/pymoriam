import logging

import httpx
from graphql import GraphQLError
from sanic.exceptions import SanicException

from memoriam.utils import scrub_headers
from memoriam.config import (
    CA_FILE, REQUEST_TIMEOUT, NO_AUTH, NO_AC,
    AUTHLY_HOST, AUTHLY_PORT, AUTHLY_SERVICENAME, AUTHLY_SERVICESECRET,
    STORAGE_SCHEME, STORAGE_HOST, STORAGE_PORT
)


AUTHLY_URL = f'https://{AUTHLY_HOST}:{AUTHLY_PORT}/api'
STORAGE_URL = f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}'


logger = logging.getLogger('memoriam')


class AuthlyClient:
    """Base class for Authly integration"""

    def __init__(self, app):
        self.app = app
        self.app.ctx.authorize = self.authorize
        self.app.ctx.service_request = self.service_request
        self.headers = {}

    def _request(self, method, url, data=None, headers=None):
        """Send a request"""
        return httpx.request(
            method=method,
            url=url,
            json=data,
            headers=headers or self.headers,
            verify=CA_FILE,
            timeout=REQUEST_TIMEOUT
        )

    def service_request(self, method, url, data=None, headers=None):
        """Send a request, re-authenticating on expired session"""
        headers = headers or {}
        response = self._request(method, url, data, {**headers, **self.headers})

        if response.status_code == 401:
            self.headers.update(
                self.service_session()
            )
            response = self._request(method, url, data, {**headers, **self.headers})

        return response

    def service_session(self):
        """Authenticate Memoriam service with Authly"""
        data = {
            'serviceName': AUTHLY_SERVICENAME,
            'serviceSecret': AUTHLY_SERVICESECRET,
        }
        url = f'{AUTHLY_URL}/auth/authenticate'

        response = httpx.post(url=url, json=data, verify=CA_FILE, timeout=REQUEST_TIMEOUT)

        if response.status_code > 400:
            raise SanicException(response.text, status_code=response.status_code)

        token = response.json().get('token')
        return {
            'Authorization': f'Bearer {token}'
        }

    def authorize(self, request, resource='', action='', graphql=False):
        """Authorize action on resource for given request against Access Control"""
        if NO_AUTH or NO_AC:
            return

        headers = {
            **scrub_headers(request.headers),
            'x-authly-resource': resource,
            'x-authly-action': action,
        }
        response = self._request('GET', f'{STORAGE_URL}/system/api/resolve', headers=headers)

        if response.status_code > 400:
            if graphql:
                raise GraphQLError('Unauthorized')
            else:
                raise SanicException('Unauthorized', status_code=401)
