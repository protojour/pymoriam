import ujson as json

from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest
from sanic import Sanic
from sanic.request import RequestParameters
from sanic.exceptions import SanicException

import memoriam.config
import memoriam.domain.rest
from memoriam.openapi import OpenAPI
from memoriam.domain.rest import RESTResolverEngine


@pytest.fixture()
def app():
    app = Sanic('test_unit_openapi_domain')
    app.update_config(memoriam.config)
    app.ctx.search = MagicMock()  # type: ignore
    app.ctx.search.get_search_subset = MagicMock(return_value='')  # type: ignore
    app.ctx.search.build_search_index = MagicMock(return_value='')  # type: ignore
    app.ctx.cache = AsyncMock()
    app.ctx.redis = AsyncMock()
    app.ctx.authorize = MagicMock()

    async def get(name, default=None):
        if name == 'rest_schema_rebuilt':
            return []
        return default

    app.ctx.cache.get = get
    app.ctx.cache.set = AsyncMock()
    return app


@pytest.fixture()
def openapi(app):
    spec_path = Path(__file__, '..', 'data', 'test_spec_unit.yml').resolve()
    schema_path = Path(__file__, '..', 'data', 'test_schema_unit.yml').resolve()
    return OpenAPI(app, spec_path=spec_path, schema_path=schema_path)


@pytest.fixture()
def engine(app, openapi, db_mock):
    app.ctx.openapi = openapi

    engine = RESTResolverEngine(app)
    engine.domain_cache = {
        'test_domain': {
            'test_name': {
                'label': 'Test name',
                'description': 'Test description',
                'resolver': 'entity',
                'attributes': {
                    'test_field': 'field'
                },
                'relations': {
                    'test_outbound': ['test_name', 'origin', 'outbound'],
                    'test_inbound': ['test_name', 'origin', 'inbound'],
                    'test_any': ['test_name', 'origin', 'any']
                },
                'triggers': ['audit']
            },
            'test_name_2': {
                'label': 'Test name 2',
                'description': 'Test description 2',
                'resolver': 'enitity'
            }
        }
    }
    return engine


@pytest.fixture()
def db_mock():
    domain_db = MagicMock()
    domain_db.aql = MagicMock(return_value={'result': []})

    test_obj = {'_id': 'test/test', '_rev': '1', '_key': 'test', '_class': 'test', 'field': 'data'}

    def aql_result(query, bind_vars=None, count=False, total=False, trx_id=None):
        if 'FOR object IN' in query:
            return {
                'total': 0,
                'result': []
            }
        if 'FOR object, edge IN' in query or 'FOR node, edge IN' in query:
            return {
                'total': 0,
                'result': []
            }
        if 'LET object = DOCUMENT' in query:
            return {
                'total': 1,
                'result': [test_obj]
            }
        if 'INSERT' in query:
            return {
                'total': 1,
                'result': [{'new': test_obj}]
            }
        if 'UPDATE' in query:
            return {
                'total': 1,
                'result': [{'old': test_obj, 'new': test_obj}]
            }
        if 'REMOVE' in query:
            return {
                'total': 1,
                'result': [{'old': test_obj}]
            }

    db = MagicMock()
    db.aql = MagicMock(side_effect=aql_result)

    async def get_arangodb(db_name=None):
        return domain_db if db_name else db

    memoriam.domain.rest.get_arangodb = get_arangodb
    return db


def test_openapiengine_init(app, openapi):

    class PatchedRESTResolverEngine(RESTResolverEngine):
        rebuild_schema = AsyncMock()

    engine = PatchedRESTResolverEngine(app)

    assert engine.app == app
    assert engine.app.ctx.rest_engine == engine


@pytest.mark.asyncio
async def test_openapiengine_rebuild_schema(app, engine, db_mock):
    spec = await engine.rebuild_schema(app)


@pytest.mark.asyncio
async def test_domain_obj_list_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = app
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.args = RequestParameters({
        'filters': ['test_field == "test"'],
        'fields': ['test_field'],
        'sort': ['test_field'],
        'skip': ['10'],
        'limit': ['10'],
    })
    assert request.args.getlist('filters') == ['test_field == "test"']
    assert request.args.get('sort') == 'test_field'
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
    }

    result = await engine.domain_obj_list_resolver(request, **kwargs)

    assert result.status == 200
    assert result.body == b'{"skip":10,"limit":10,"results_total":0,"results":[]}'


@pytest.mark.asyncio
async def test_domain_obj_post_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    request.json = {'test': 'test'}
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
    }

    result = await engine.domain_obj_post_resolver(request, **kwargs)

    assert result.status == 201
    assert result.body == b'{"_key":"test","_class":"test","test_field":"data"}'


@pytest.mark.asyncio
async def test_domain_obj_get_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = app
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test'
    }

    result = await engine.domain_obj_get_resolver(request, **kwargs)

    assert result.status == 200
    assert result.body == b'{"_key":"test","_class":"test","test_field":"data"}'


@pytest.mark.asyncio
async def test_domain_obj_patch_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test'
    }

    result = await engine.domain_obj_patch_resolver(request, **kwargs)

    assert result.status == 200
    assert result.body == b'{"_key":"test","_class":"test","test_field":"data"}'


@pytest.mark.asyncio
async def test_domain_obj_delete_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test'
    }

    result = await engine.domain_obj_delete_resolver(request, **kwargs)

    assert result.status == 204


@pytest.mark.asyncio
async def test_relation_list_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = app
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.args = RequestParameters({
        'filters': ['test_field == "test"'],
        'fields': ['test_field'],
        'sort': ['test_field'],
        'skip': ['10'],
        'limit': ['10'],
    })
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_outbound'
    }

    result = await engine.relation_list_resolver(request, **kwargs)

    assert result.status == 200
    assert result.body == b'{"skip":10,"limit":10,"results_total":0,"results":[]}'


@pytest.mark.asyncio
async def test_relation_post_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    request.json = {'to_class': 'test_name_2', 'to_key': '2', 'additional': 'property'}
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_outbound'
    }

    result = await engine.relation_post_resolver(request, **kwargs)

    assert result.status == 201

    request.json = {'from_class': 'test_name_2', 'from_key': '2', 'additional': 'property'}
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_inbound'
    }

    result = await engine.relation_post_resolver(request, **kwargs)

    assert result.status == 201

    request.json = {'other_class': 'test_name_2', 'other_key': '2', 'direction': 'outbound', 'additional': 'property'}
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_any'
    }

    result = await engine.relation_post_resolver(request, **kwargs)

    assert result.status == 201


@pytest.mark.asyncio
async def test_relation_patch_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    request.json = {'to_class': 'test_name_2', 'to_key': '2', 'additional': 'updated property'}
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_outbound'
    }

    result = await engine.relation_patch_resolver(request, **kwargs)

    assert result.status == 204

    request.json = {'from_class': 'test_name_2', 'from_key': '2', 'additional': 'updated property'}
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_inbound'
    }

    result = await engine.relation_patch_resolver(request, **kwargs)

    assert result.status == 204

    request.json = {'other_class': 'test_name_2', 'other_key': '2', 'direction': 'outbound', 'additional': 'updated property'}
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_any'
    }

    result = await engine.relation_patch_resolver(request, **kwargs)

    assert result.status == 204


@pytest.mark.asyncio
async def test_relation_delete_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    request.args = RequestParameters({
        'to_class': ['test_name_2'],
        'to_key': ['2']
    })
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_outbound'
    }

    result = await engine.relation_delete_resolver(request, **kwargs)

    assert result.status == 204

    request.args = RequestParameters({
        'from_class': ['test_name_2'],
        'from_key': ['2']
    })
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_inbound'
    }

    result = await engine.relation_delete_resolver(request, **kwargs)

    assert result.status == 204

    request.args = RequestParameters({
        'other_class': ['test_name_2'],
        'other_key': ['2'],
        'direction': ['outbound']
    })
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
        'relation': 'test_any'
    }

    result = await engine.relation_delete_resolver(request, **kwargs)

    assert result.status == 204


@pytest.mark.asyncio
async def test_neighbors_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
    }

    result = await engine.neighbors_resolver(request, **kwargs)

    assert result.status == 200
    assert json.loads(result.body) == { 'nodes': [], 'edges': [] }


@pytest.mark.asyncio
async def test_changes_resolver(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name',
        '_key': 'test',
    }

    result = await engine.changes_resolver(request, **kwargs)

    assert result.status == 200


@pytest.mark.asyncio
async def test_changes_resolver_fails_without_audit_trigger(app, engine, db_mock):
    request = MagicMock()
    request.app = MagicMock()
    request.app.ctx.cache = app.ctx.cache
    request.app.ctx.authorize = app.ctx.authorize
    request.app.add_task = MagicMock()
    kwargs = {
        'domain': 'test_domain',
        'domain_class': 'test_name_2',
        '_key': 'test',
    }

    with pytest.raises(SanicException) as excinfo:
        await engine.changes_resolver(request, **kwargs)

    assert excinfo.value.status_code == 404
