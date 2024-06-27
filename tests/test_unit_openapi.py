from pathlib import Path

import pytest

from sanic import Sanic, response

import memoriam.config
from memoriam.openapi import OpenAPI


DATA_PATH = Path(__file__, '..', 'data').resolve()


@pytest.fixture()
def app():
    app = Sanic('test_unit_openapi')
    app.update_config(memoriam.config)
    app.config.AUTO_EXTEND = False
    return app


@pytest.fixture()
def api(app):
    spec_path = Path(__file__, '..', 'data', 'test_spec_unit.yml').resolve()
    schema_path = Path(__file__, '..', 'data', 'test_schema_unit.yml').resolve()
    return OpenAPI(app, spec_path=spec_path, schema_path=schema_path)


def test_init_openapi(app, api):
    assert api.app == app
    assert api.base_url == '/api'
    assert api.spec_url == '/api/openapi.json'
    assert api.namespace == 'default'
    assert api.specs
    assert api.specs['default']['openapi'] == '3.1.0'
    assert api.specs['default']['info']
    assert api.specs['default']['servers']
    assert api.specs['default']['tags']
    assert api.specs['default']['components']['parameters']
    assert api.specs['default']['components']['schemas']
    assert api.specs['default']['paths']
    assert api.template
    assert api.template.render(spec_url=api.spec_url).startswith('<!DOCTYPE html>')
    assert api.validation_schema
    assert api.validators
    assert api.validators['/api/data:get']
    assert api.validators['/api/data:post']


@pytest.mark.asyncio
async def test_openapi_spec(app, api):
    request, response = await app.asgi_client.get('/api')
    assert response.status == 200


@pytest.mark.asyncio
async def test_openapi_ui(app, api):
    request, response = await app.asgi_client.get('/api/openapi.json')
    assert response.status == 200


def test_ref_resolver(app, api):
    test_ref = {'type': 'object'}
    resolved = api.ref_resolver(test_ref)
    assert resolved == test_ref

    test_ref = {'$ref': '#/components/parameters/_key'}
    resolved = api.ref_resolver(test_ref)
    assert resolved == api.specs['default']['components']['parameters']['_key']

    test_ref = {'$ref': '#/components/schemas/data'}
    resolved = api.ref_resolver(test_ref)
    assert resolved == api.specs['default']['components']['schemas']['data']


async def list_data(request):
    return response.json({'status': 'ok'})


async def post_data(request):
    return response.json(request.json, 201)


async def get_data(request, _key):
    return response.json({'status': 'ok', '_key': _key})


@pytest.mark.asyncio
async def test_openapi_endpoints(app, api):
    request, response = await app.asgi_client.get('/api/data')
    assert response.status == 200
    assert response.json['status'] == 'ok'

    # not a number
    data = {'test_a': 'a'}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 400

    # number
    data = {'test_a': 1}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 201

    # number
    data = {'test_a': 1.01}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 201

    # not an integer
    data = {'test_b': 'a'}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 400

    # not an integer
    data = {'test_b': 1.01}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 400

    # integer
    data = {'test_b': 1}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 201

    # not a boolean
    data = {'test_c': 1}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 400

    # not a boolean
    data = {'test_c': 'true'}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 400

    # boolean
    data = {'test_c': True}
    request, response = await app.asgi_client.post('/api/data', json=data)
    assert response.status == 201

    request, response = await app.asgi_client.get('/api/data/123')
    assert response.status == 200
    assert response.json
    assert response.json['status'] == 'ok'
    assert response.json['_key'] == '123'
