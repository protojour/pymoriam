import pytest
from sanic import Sanic

import memoriam.config
from memoriam.domain.search import ArangoSearch


@pytest.fixture()
def app():
    app = Sanic('test_unit_search')
    app.update_config(memoriam.config)
    return app


@pytest.fixture()
def search(app):
    arangosearch = ArangoSearch(app)
    return arangosearch


def test_arangosearch_init(app, search):
    assert search.app == app
    assert search.app.ctx.search == search
    assert search.config


def test_get_search_subset(search):
    obj = {}
    search_query = ''
    bind_vars = {}
    result = search.get_search_subset(search_query, obj, bind_vars)
    assert result == ''
    assert bind_vars == {}

    obj = {
        'resolver': 'test'
    }
    search_query = 'test'
    bind_vars = {}
    result = search.get_search_subset(search_query, obj, bind_vars)
    assert 'LET test =' in result
    assert 'FOR result IN memoriam_text_search' in result
    assert 'collections: ["test"]' in result
    assert bind_vars.get('search') == 'test'

    bind_vars = {}
    result = search.get_search_subset(search_query, obj, bind_vars, True)
    assert 'collections: ["source","ruleset","data"' in result


def test_build_search_index(search):
    search.index_fields = {
        'entity': ['one', 'two']
    }
    collection = 'entity'
    obj = {
        'one': 'some data',
        'two': 'more data'
    }
    _index = search.build_search_index(collection, obj)
    assert _index == 'some data more data'
