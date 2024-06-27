import pytest

from sanic.response import empty
from sanic_testing import TestManager

import memoriam.gateway.app
from memoriam.gateway.app import init_app

pytestmark = pytest.mark.filterwarnings('ignore::DeprecationWarning')


@pytest.fixture(scope='module')
def app():
    reverse_proxy = lambda request, path: empty(200)
    memoriam.gateway.app.get_reverse_proxy = lambda base_url, name: reverse_proxy

    app = init_app()
    app.config.AUTO_EXTEND = False
    app.config.NO_AUTH = False

    TestManager(app)
    return app


def test_allowed_paths(app):
    kwargs = {'motd': False}

    _, response = app.test_client.get('/system/api', debug=True, server_kwargs=kwargs)
    assert response.status == 200

    _, response = app.test_client.get('/system/api/openapi.json', debug=True, server_kwargs=kwargs)
    assert response.status == 200

    _, response = app.test_client.get('/test_domain/api', debug=True, server_kwargs=kwargs)
    assert response.status == 200

    _, response = app.test_client.get('/test_domain/api/openapi.json', debug=True, server_kwargs=kwargs)
    assert response.status == 200

    _, response = app.test_client.post('/authly/api/auth/authenticate', debug=True, server_kwargs=kwargs)
    assert response.status == 200

    _, response = app.test_client.get('/authly/api/auth/session', debug=True, server_kwargs=kwargs)
    assert response.status == 200


def test_disallowed_paths(app):
    kwargs = {'motd': False}
    _, response = app.test_client.get('/system/api/domain', debug=True, server_kwargs=kwargs)
    assert response.status == 401

    _, response = app.test_client.get('/system/api/service', debug=True, server_kwargs=kwargs)
    assert response.status == 401

    _, response = app.test_client.get('/test_domain/graphql', debug=True, server_kwargs=kwargs)
    assert response.status == 401

    _, response = app.test_client.get('/_db/_system/_api/version', debug=True, server_kwargs=kwargs)
    assert response.status == 401

    _, response = app.test_client.get('/_api/version', debug=True, server_kwargs=kwargs)
    assert response.status == 401
