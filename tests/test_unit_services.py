from unittest.mock import MagicMock

import pytest
from cashews import cache
from sanic.exceptions import InvalidUsage, NotFound

import memoriam.config
import memoriam.domain.services
from memoriam.domain.services import *


@pytest.mark.asyncio
async def test_init_services():
    pass


@pytest.mark.asyncio
async def test_register_service():
    cache.setup(**memoriam.config.CACHE_CONFIG)
    cache.default_prefix = 'memoriam'

    request = MagicMock()
    request.app.ctx.cache = cache
    request.app.ctx.authorize = MagicMock()
    request.json = {}

    with pytest.raises(InvalidUsage):
        result = await register_service(request)
        assert result.status == 400

    request = MagicMock()
    request.app.ctx.cache = cache
    request.app.ctx.authorize = MagicMock()

    request.json = {
        'name': 'Test Service',
        'info': 'test',
        'host': 'testhost',
        'api': '/test',
    }

    result = await register_service(request)
    assert result.status == 201
    assert result.body == rb'{}'


@pytest.mark.asyncio
async def test_service_status():
    cache.setup(**memoriam.config.CACHE_CONFIG)
    cache.default_prefix = 'memoriam'

    request = MagicMock()
    request.app.ctx.cache = cache
    request.app.ctx.authorize = MagicMock()

    result = await service_status(request)
    assert result.status == 200
    assert result.body == b'{"test_service":{"name":"Test Service","info":"test","host":"testhost","api":"testhost\/test"}}'


@pytest.mark.asyncio
async def test_service_api_proxy():
    cache.setup(**memoriam.config.CACHE_CONFIG)
    cache.default_prefix = 'memoriam'

    request = MagicMock()
    request.app.ctx.cache = cache
    request.app.ctx.authorize = MagicMock()

    name = 'no_service'
    path = 'no_path'

    with pytest.raises(NotFound):
        result = await service_api_proxy(request, name, path)
        assert result.status == 404

    a = MagicMock()
    a.__aenter__.return_value.request.return_value.headers = {}
    memoriam.domain.services.httpx.AsyncClient = MagicMock(return_value=a)
    memoriam.domain.services.raw = MagicMock()
    request = MagicMock()
    request.app.ctx.cache = cache
    request.app.ctx.authorize = MagicMock()

    request.method = 'GET'
    request.query_string = 'test=1'
    request.body = 'body'
    request.headers = {}
    name = 'test_service'
    path = 'test_path'

    result = await service_api_proxy(request, name, path)
    assert a.__aenter__.return_value.request.await_count == 1
    assert a.__aenter__.return_value.request.await_args.kwargs == {
        'method': 'GET',
        'url': 'testhost/test_path?test=1',
        'content': 'body',
        'headers': {}
    }
    assert memoriam.domain.services.raw.call_count == 1


@pytest.mark.asyncio
async def test_unregister_service():
    cache.setup(**memoriam.config.CACHE_CONFIG)
    cache.default_prefix = 'memoriam'

    request = MagicMock()
    request.app.ctx.cache = cache
    request.app.ctx.authorize = MagicMock()

    with pytest.raises(NotFound):
        result = await unregister_service(request, 'no_service')
        assert result.status == 404

    request = MagicMock()
    request.app.ctx.cache = cache
    request.app.ctx.authorize = MagicMock()

    result = await unregister_service(request, 'test_service')
    assert result.status == 204
