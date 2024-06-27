import time

import pytest

from tests.conftest import domain_url


@pytest.fixture(scope='module')
def search_data(clean_db, http_client):

    # create obj
    obj = {
        'name': 'test',
        'description': 'data data data',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/dataset', json=obj)
    assert response.status_code == 201, response.json()

    # create another obj
    obj = {
        'content': 'tests are nice',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/comment', json=obj)
    assert response.status_code == 201, response.json()

    time.sleep(2)


def test_search_openapi(search_data, http_client):

    # no search
    response = http_client.get(f'{domain_url}/infoflow/api/search')
    assert response.status_code == 400, response.json()

    # search with results
    response = http_client.get(f'{domain_url}/infoflow/api/search?search=test')
    assert response.status_code == 200, response.json()
    assert len(response.json().get('results')) == 2

    # search without results
    response = http_client.get(f'{domain_url}/infoflow/api/search?search=blag')
    assert response.status_code == 200, response.json()
    assert len(response.json().get('results')) == 0
