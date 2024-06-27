from unittest.mock import MagicMock, AsyncMock

import pytest
from sanic import Sanic
from graphql import GraphQLError

import memoriam.config
import memoriam.domain.graphql
from memoriam.domain.graphql import GraphQLResolverEngine


@pytest.fixture()
def app():
    app = Sanic('test_unit_graphql')
    app.update_config(memoriam.config)
    app.config.AUTO_EXTEND = False
    app.ctx.search = MagicMock()  # type: ignore
    app.ctx.search.get_search_subset = MagicMock(return_value='')  # type: ignore
    app.ctx.search.build_search_index = MagicMock(return_value='')  # type: ignore
    app.ctx.cache = AsyncMock()
    app.ctx.redis = AsyncMock()
    app.ctx.authorize = MagicMock()

    async def get(name, default):
        return default

    app.ctx.cache.get = get

    return app


@pytest.fixture()
def engine(app):
    domain_db = MagicMock()
    domain_db.aql = MagicMock(return_value={'result': []})

    def set_domains(self, domains):
        domain_db.aql = MagicMock(return_value={'result': domains})

    GraphQLResolverEngine.set_domains = set_domains  # type: ignore

    test_obj = {'_id': 'test/test', '_rev': '1', '_key': 'test', '_class': 'test', 'field': 'data'}

    def aql_result(query, bind_vars=None, count=False, total=False, trx_id=None):
        if 'FOR object IN' in query:
            return {
                'total': 0,
                'result': []
            }
        if 'RETURN DOCUMENT' in query:
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

    memoriam.domain.graphql.get_arangodb = get_arangodb

    return GraphQLResolverEngine(app)


@pytest.fixture()
def engine_cache(engine):
    engine.cache = MagicMock()
    engine.cache.get = AsyncMock(return_value=[])
    engine.cache.set = AsyncMock()


def test_graphqlengine_init(app):

    class PatchedGraphQLResolverEngine(GraphQLResolverEngine):
        rebuild_schema = AsyncMock()

    engine = PatchedGraphQLResolverEngine(app)

    # assert PatchedGraphQLResolverEngine.rebuild_schema.call_count == 1
    assert engine.app == app
    assert engine.app.ctx.graphql_engine == engine
    assert engine.db_schema
    assert engine.db_schema['collections']
    assert engine.db_schema['edge_collections']
    assert '<!DOCTYPE html>' in engine.graphiql_html
    assert app.router.find_route_by_view_name('graphql_graphiql')
    assert app.router.find_route_by_view_name('graphql_server')


@pytest.mark.asyncio
async def test_graphqlengine_rebuild_schema(app, engine):
    domains = [{
        'label': 'TestDomain',
        'description': 'Test description',
        'active': True,
        'schema': '''
            test_domain_class:
                description: description
                resolver: entity
                attributes:
                    test_field: data
                relations:
                    rel_a: [[test_aa, test_ab, test_ac], includes, outbound]
                    rel_b: [[ANY], includes, outbound]
                    rel_c: [[test_aa], includes, outbound]
                    rel_d: [ANY, includes, outbound]
                    rel_e: [test_aa, includes, outbound]

            test_aa:
                description: ''
                resolver: entity
                attributes: {}
                relations: {}

            test_ab:
                description: ''
                resolver: entity
                attributes: {}
                relations: {}

            test_ac:
                description: ''
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }]
    engine.set_domains(domains)

    await engine.rebuild_schema(app)

    domain = engine.schemas['test_domain'].type_map.get('Query')
    assert domain
    assert domain.fields['TestDomainClass']
    assert domain.fields['TestDomainClassList']
    assert domain.fields['TestAa']
    assert domain.fields['TestAaList']
    assert domain.fields['TestAb']
    assert domain.fields['TestAbList']
    assert domain.fields['TestAc']
    assert domain.fields['TestAcList']

    domain_class = engine.schemas['test_domain'].type_map.get('TestDomainClass')
    assert domain_class
    assert domain_class.fields['test_field']
    assert domain_class.fields['rel_a']
    assert domain_class.fields['rel_b']
    assert domain_class.fields['rel_c']
    assert domain_class.fields['rel_d']
    assert domain_class.fields['rel_e']

    rel_a_union = engine.schemas['test_domain'].type_map.get('TestDomainClassRelAUnion')
    assert rel_a_union
    assert rel_a_union.types[0].name == 'TestAa'
    assert rel_a_union.types[1].name == 'TestAb'
    assert rel_a_union.types[2].name == 'TestAc'

    any_union = engine.schemas['test_domain'].type_map.get('TestDomainAny')
    assert any_union
    assert any_union.types[0].name == 'TestDomainClass'
    assert any_union.types[1].name == 'TestAa'
    assert any_union.types[2].name == 'TestAb'
    assert any_union.types[3].name == 'TestAc'

    assert engine.schemas['test_domain'].type_map.get('TestAa')
    assert engine.schemas['test_domain'].type_map.get('TestAb')
    assert engine.schemas['test_domain'].type_map.get('TestAc')


def test_graphqlengine_get_field_type(app, engine):
    engine.db_schema = {
        'collections': {
            'test_collection': {
                'properties': {
                    'test_a': {
                        'type': 'string'
                    },
                    'test_b': {
                        'type': 'object',
                        'properties': {

                        }
                    },
                    'test_c': {
                        'type': 'array',
                        'items': {
                            'type': 'integer'
                        }
                    },
                    'test_d': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {}
                        }
                    }
                }
            }
        }
    }
    db_attrs = engine.db_schema['collections']['test_collection']['properties']
    assert engine.get_field_type('test_field', 'test_a', db_attrs['test_a']) == 'String'
    assert engine.get_field_type('test_field', 'test_b', db_attrs['test_b']) == 'TestField'
    assert engine.get_field_type('test_field', 'test_c', db_attrs['test_c']) == 'Int'
    assert engine.get_field_type('test_field', 'test_d', db_attrs['test_d']) == 'TestField'


@pytest.mark.asyncio
async def test_graphqlengine_get_object_resolver(app, engine):
    db = MagicMock()
    result = {
        'total': 0,
        'result': [],
    }
    db.aql = MagicMock(return_value=result)
    memoriam.domain.graphql.get_arangodb = AsyncMock(return_value=db)
    info = MagicMock()
    info.context = MagicMock()
    info.context.app = app
    info.context.app.ctx.authorize = app.ctx.authorize
    info.context.json = {}
    domain_spec = {
        'test': {
            'resolver': 'entity',
            'attributes': {
                'domain_field': 'field'
            }
        }
    }

    resolver = engine.get_object_resolver(domain_spec, 'test', domain_spec['test'])

    result = await resolver(None, info, _key='test')
    assert result is None
    assert db.aql.call_count == 1

    result = await resolver(None, info)
    assert result == {'results_total': 0, 'results': []}
    assert db.aql.call_count == 2

    data = [{
        '_key': 'test',
        '_class': 'class'
    }]

    result = {
        'total': 1,
        'result': data,
    }
    db.aql = MagicMock(return_value=result)
    result = await resolver(None, info, _key='test')
    assert result == data[0]
    assert db.aql.call_count == 1
    assert 'RETURN object' in db.aql.call_args.args[0]

    result = await resolver(None, info)
    assert result == {'results_total': 1, 'results': data}
    assert db.aql.call_count == 2
    assert 'FILTER object._class' in db.aql.call_args.args[0]
    assert 'LIMIT 0, %s' % memoriam.config.ARANGO_DEFAULT_LIMIT in db.aql.call_args.args[0]

    result = await resolver(None, info, skip=20, limit=10)
    assert result == {'results_total': 1, 'results': data}
    assert db.aql.call_count == 3
    assert 'LIMIT 20, 10' in db.aql.call_args.args[0]

    with pytest.raises(GraphQLError):
        result = await resolver(None, info, filter=['test == "a"'])

    result = await resolver(None, info, filter=['domain_field == "a"'])
    assert result == {'results_total': 1, 'results': data}
    assert db.aql.call_count == 4
    assert 'FILTER object.field == @object_field_comp_1' in db.aql.call_args.args[0]

    with pytest.raises(GraphQLError):
        result = await resolver(None, info, sort=['test'])

    result = await resolver(None, info, sort=['domain_field'])
    assert result == {'results_total': 1, 'results': data}
    assert db.aql.call_count == 5
    assert 'SORT object.field, object._key' in db.aql.call_args.args[0]

    result = await resolver(None, info, sort=['-domain_field'])
    assert result == {'results_total': 1, 'results': data}
    assert db.aql.call_count == 6
    assert db.aql.call_args.args[0]
    assert 'SORT object.field DESC, object._key' in db.aql.call_args.args[0]


@pytest.mark.asyncio
async def test_graphqlengine_get_field_resolver(app, engine):
    field_name = 'field_name'
    resolver = engine.get_field_resolver(field_name)

    obj = {}
    result = await resolver(obj, None)
    assert result is None

    obj = {'field_name': 'test'}
    result = await resolver(obj, None)
    assert result == 'test'


@pytest.mark.asyncio
async def test_graphqlengine_get_edge_resolver(app, engine):
    data = {'random': 'data'}
    db = MagicMock()
    result = {
        'total': 1,
        'result': [data],
    }
    db.aql = MagicMock(return_value=result)
    memoriam.domain.graphql.get_arangodb = AsyncMock(return_value=db)
    info = MagicMock()
    info.context = MagicMock()
    info.context.app = app
    info.context.app.ctx.authorize = app.ctx.authorize
    domain_spec = {
        'test': {
            'resolver': 'entity',
            'attributes': {},
            'relations': {
                'test_relation_a': ['test', 'origin', 'outbound'],
                'test_relation_b': [['test'], 'origin', 'outbound']
            },
        }
    }
    class_spec = domain_spec['test']

    field_name = 'test_relation_a'
    resolver = engine.get_edge_resolver(domain_spec, class_spec, field_name)
    obj = {'_id': 'test'}
    result = await resolver(obj, info)
    assert result == data

    field_name = 'test_relation_b'
    resolver = engine.get_edge_resolver(domain_spec, class_spec, field_name)
    obj = {'_id': 'test'}
    result = await resolver(obj, info)
    assert result == {'results_total': 1, 'results': [data]}


@pytest.mark.asyncio
async def test_graphqlengine_get_mutation_resolver(app, engine):
    data = {
        '_key': 'test',
        '_class': 'class'
    }

    wrapped_data = {
        'old': data,
        'new': data,
    }

    db = MagicMock()
    result = {
        'total': 0,
        'result': [wrapped_data],
    }
    db.aql = MagicMock(return_value=result)
    memoriam.domain.graphql.get_arangodb = AsyncMock(return_value=db)
    info = MagicMock()
    info.context = MagicMock()
    info.context.app = MagicMock()
    info.context.app.add_task = MagicMock()
    info.context.app.ctx.cache = app.ctx.cache
    info.context.app.ctx.authorize = app.ctx.authorize
    class_spec = {
        'resolver': 'entity',
        'attributes': {}
    }

    db.aql.side_effect = Exception('Database not found')
    resolver = engine.get_mutation_resolver('class', class_spec, 'create', 'Test')
    with pytest.raises(Exception) as e:
        result = await resolver(None, info)
        assert 'Database not found' in str(e)

    db.aql.side_effect = None
    resolver = engine.get_mutation_resolver('class', class_spec, 'create', 'Test')
    result = await resolver(None, info)
    assert result == data
    assert db.aql.call_count == 2
    assert '{"_class":"class"}' in db.aql.call_args[0][0]

    resolver = engine.get_mutation_resolver('class', class_spec, 'update', 'Test')
    result = await resolver(None, info)
    assert result == data
    assert db.aql.call_count == 3

    resolver = engine.get_mutation_resolver('class', class_spec, 'delete', 'Test')
    result = await resolver(None, info, _key='test')
    assert result is True
    assert db.aql.call_count == 4


@pytest.mark.asyncio
async def test_graphqlengine_get_edge_mutation_resolver(app, engine):
    data = {
        '_key': 'test',
        '_from': 'test/1',
        '_to': 'test/2'
    }

    wrapped_data = {
        'old': data,
        'new': data,
    }

    db = MagicMock()
    result = {
        'total': 0,
        'result': [wrapped_data],
    }
    db.aql = MagicMock(return_value=result)
    memoriam.domain.graphql.get_arangodb = AsyncMock(return_value=db)

    info = MagicMock()
    info.context = MagicMock()
    info.context.app = app
    info.context.app.ctx.authorize = app.ctx.authorize
    class_spec = {
        'resolver': 'entity',
        'attributes': {}
    }

    engine.type_resolver = {
        'Test': 'test'
    }
    kwargs = {
        'from': {
            'type': 'Test',
            '_key': '1'
        },
        'to': {
            'type': 'Test',
            '_key': '2'
        },
    }

    resolver = engine.get_edge_mutation_resolver(class_spec, 'attach', 'origin')
    result = await resolver(None, info, **kwargs)
    assert result is True
    assert db.aql.call_count == 1

    resolver = engine.get_edge_mutation_resolver(class_spec, 'detach', 'origin')
    result = await resolver(None, info, **kwargs)
    assert result is True
    assert db.aql.call_count == 2


@pytest.mark.asyncio
async def test_graphqlengine_graphql_playground(app, engine):
    request, response = await app.asgi_client.get('/test_domain/graphql')
    assert response.status == 200, response.text
    assert '<!DOCTYPE html>' in response.text


@pytest.mark.asyncio
async def test_graphqlengine_graphql_server(app, engine, engine_cache):
    data = {'query': '{ version }'}
    request, response = await app.asgi_client.post('/test_domain/graphql', json=data)
    assert response.status == 404, response.text
