import os
import time

import httpx
import pytest

from sanic import Sanic

from memoriam.config import GATEWAY_PORT, DOMAIN_PORT, STORAGE_PORT, ARANGO_PORT
from memoriam.arangodb import ArangoHTTPClient


Sanic.test_mode = True

pytest_plugins = ['env']

gateway_url = f'https://{os.getenv("LOCALHOST", "localhost")}:{GATEWAY_PORT}'
domain_url = f'http://{os.getenv("LOCALHOST", "localhost")}:{DOMAIN_PORT}'
storage_url = f'http://{os.getenv("LOCALHOST", "localhost")}:{STORAGE_PORT}'
arango_url = f'http://{os.getenv("LOCALHOST", "localhost")}:{ARANGO_PORT}'


@pytest.fixture(scope='session')
def http_client():
    headers = {
        'x-authly-entity-id': 'memoriam',
        'x-authly-entity-type': 'Service',
    }

    client = httpx.Client(verify=False, headers=headers)
    yield client

    client.close()


@pytest.fixture(scope='session')
def wait_for_system_api(http_client):
    """Wait for the API to become responsive"""
    for retry in range(40):
        try:
            response = http_client.get(f'{domain_url}/health')
            assert response.status_code == 200, response.text
            break
        except httpx.HTTPError:
            time.sleep(.5)


@pytest.fixture(scope='session')
def wait_for_storage_api(http_client):
    """Wait for the API to become responsive"""
    for retry in range(40):
        try:
            response = http_client.get(f'{storage_url}/health')
            assert response.status_code == 200, response.text
            break
        except httpx.HTTPError:
            time.sleep(.5)


@pytest.fixture(scope='module')
def db(wait_for_storage_api):
    return ArangoHTTPClient(
        hosts=[arango_url],
        db_name='memoriam_test',
        auth=('root', 'secret'),
    )


@pytest.fixture(scope='module')
def clean_db(db):
    collections = db.list_collections()['result']
    for collection in collections:
        if collection['name'].startswith('_'):
            continue
        if collection['name'] == 'domain':
            continue
        db.truncate_collection(collection['name'])
