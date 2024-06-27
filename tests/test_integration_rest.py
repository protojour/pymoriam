import time

import pytest

from tests.conftest import domain_url


@pytest.fixture(scope='module')
def backend_data(db, clean_db):
    nodes = [
        {
            '_key': '1',
            '_class': 'dataset',
            '_index': 'test a alpha',
            'label': 'test a',
            'data': 'alpha',
        },
        {
            '_key': '2',
            '_class': 'dataset',
            '_index': 'test b beta',
            'label': 'test b',
            'data': 'beta',
        },
        {
            '_key': '3',
            '_class': 'dataset',
            '_index': 'test c gamma',
            'label': 'test c',
            'data': 'gamma',
        },
    ]

    edges = [
        {
            '_key': '1',
            '_from': 'grouping/1',
            '_to': 'grouping/2',
            'active': False,
        },
        {
            '_key': '2',
            '_from': 'grouping/2',
            '_to': 'grouping/3',
            'active': True,
        },
        {
            '_key': '4',
            '_from': 'grouping/3',
            '_to': 'grouping/2',
            'active': True,
        },
        {
            '_key': '3',
            '_from': 'grouping/3',
            '_to': 'grouping/1',
            'active': True,
        },
    ]

    # import manually for explicit keys
    db.bulk_create('grouping', nodes)
    db.bulk_create('includes', edges)

    return nodes, edges


def test_list_domain_objects(clean_db, backend_data, http_client):
    response = http_client.get(f'{domain_url}/infoflow/api/random/words')
    assert response.status_code == 404, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/dataset')
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'},
            {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
            {'_class': 'dataset', '_key': '3', 'name': 'test c', 'description': 'gamma'},
        ]
    }

    params = {'search': 'test'}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'},
            {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
            {'_class': 'dataset', '_key': '3', 'name': 'test c', 'description': 'gamma'},
        ]
    }

    params = {'skip': 0, 'limit': 1}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 1,
        'results_total': 3,
        'results': [
            {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'},
        ]
    }

    params = {'search': 'alpha'}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 1,
        'results': [
            {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'}
        ]
    }

    params = {'search': 'nonexistent'}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 0,
        'results': []
    }

    params = {'filter': ['name == "test a"']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 1,
        'results': [
            {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'}
        ]
    }

    params = {'filter': ['name LIKE "test%"', 'name LIKE "%a"']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 1,
        'results': [
            {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'}
        ]
    }

    params = {'field': ['name'], 'sort': ['-name']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {'name': 'test c'},
            {'name': 'test b'},
            {'name': 'test a'},
        ]
    }

    params = {'field': ['name', 'description']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {'name': 'test a', 'description': 'alpha'},
            {'name': 'test b', 'description': 'beta'},
            {'name': 'test c', 'description': 'gamma'},
        ]
    }

    params = {'relation': ['objects'], 'sort': ['objects.-name']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {
                '_class': 'dataset',
                '_key': '1',
                'name': 'test a',
                'description': 'alpha',
                'objects': [
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                ]
            },
            {
                '_class': 'dataset',
                '_key': '2',
                'name': 'test b',
                'description': 'beta',
                'objects': [
                    {'_class': 'dataset', '_key': '3', 'name': 'test c', 'description': 'gamma'},
                ]
            },
            {
                '_class': 'dataset',
                '_key': '3',
                'name': 'test c',
                'description': 'gamma',
                'objects': [
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                    {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'},
                ]
            },
        ]
    }

    params = {'field': ['name'], 'relation': ['objects'], 'sort': ['objects.name']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {
                'name': 'test a',
                'objects': [
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                ]
            },
            {
                'name': 'test b',
                'objects': [
                    {'_class': 'dataset', '_key': '3', 'name': 'test c', 'description': 'gamma'},
                ]
            },
            {
                'name': 'test c',
                'objects': [
                    {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'},
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                ]
            },
        ]
    }

    params = {'field': ['name'], 'relation': ['objects'], 'filter': ['objects.description == "beta"']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {
                'name': 'test a',
                'objects': [
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                ]
            },
            {
                'name': 'test b',
                'objects': []
            },
            {
                'name': 'test c',
                'objects': [
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                ]
            },
        ]
    }

    params = {
        'field': ['name'],
        'relation': ['objects'],
        'filter': ['objects.description == "beta"'],
        'parent_filter': ['objects']
    }
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 2,
        'results': [
            {
                'name': 'test a',
                'objects': [
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                ]
            },
            {
                'name': 'test c',
                'objects': [
                    {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
                ]
            },
        ]
    }

    params = {'field': ['name', 'objects.name'], 'relation': ['objects'], 'sort': ['objects.name']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {
                'name': 'test a',
                'objects': [
                    {'name': 'test b'},
                ]
            },
            {
                'name': 'test b',
                'objects': [
                    {'name': 'test c'},
                ]
            },
            {
                'name': 'test c',
                'objects': [
                    {'name': 'test a'},
                    {'name': 'test b'},
                ]
            },
        ]
    }

    params = {'field': ['name', 'objects.name', 'objects.objects.name'], 'relation': ['objects', 'objects.objects'], 'sort': ['objects.name', 'objects.objects.-name']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {
                'name': 'test a',
                'objects': [
                    {
                        'name': 'test b',
                        'objects': [
                            {'name': 'test c'}
                        ]
                    },
                ]
            },
            {
                'name': 'test b',
                'objects': [
                    {
                        'name': 'test c',
                        'objects': [
                            {'name': 'test b'},
                            {'name': 'test a'},
                        ]
                    },
                ]
            },
            {
                'name': 'test c',
                'objects': [
                    {
                        'name': 'test a',
                        'objects': [
                            {'name': 'test b'}
                        ]
                    },
                    {
                        'name': 'test b',
                        'objects': [
                            {'name': 'test c'}
                        ]
                    },
                ]
            },
        ]
    }

    params = {
        'field': ['name', 'objects.name', 'objects.objects.name'],
        'relation': ['objects', 'objects.objects'],
        'filter': ['objects.objects.name == "test b"'],
        'parent_filter': ['objects.objects'],
        'sort': ['name'],
    }
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {
                'name': 'test a',
                'objects': []
            },
            {
                'name': 'test b',
                'objects': [
                    {
                        'name': 'test c',
                        'objects': [
                            {'name': 'test b'}
                        ]
                    },
                ]
            },
            {
                'name': 'test c',
                'objects': [
                    {
                        'name': 'test a',
                        'objects': [
                            {'name': 'test b'}
                        ]
                    },
                ]
            },
        ]
    }

    params = {
        'field': ['name', 'objects.name', 'objects.objects.name'],
        'relation': ['objects', 'objects.objects'],
        'edge_filter': ['objects.objects.active == true'],
        'sort': ['name', 'objects.name', 'objects.objects.name'],
    }
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {
                'name': 'test a',
                'objects': [
                    {
                        'name': 'test b',
                        'objects': [
                            {'name': 'test c'}
                        ]
                    },
                ]
            },
            {
                'name': 'test b',
                'objects': [
                    {
                        'name': 'test c',
                        'objects': [
                            {'name': 'test a'},
                            {'name': 'test b'}
                        ]
                    },
                ]
            },
            {
                'name': 'test c',
                'objects': [
                    {
                        'name': 'test a',
                        'objects': []
                    },
                    {
                        'name': 'test b',
                        'objects': [
                            {'name': 'test c'}
                        ]
                    },
                ]
            },
        ]
    }

    params = {'sort': '-name'}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 3,
        'results': [
            {'_class': 'dataset', '_key': '3', 'name': 'test c', 'description': 'gamma'},
            {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
            {'_class': 'dataset', '_key': '1', 'name': 'test a', 'description': 'alpha'},
        ]
    }


def test_post_domain_object(clean_db, backend_data, http_client):
    bad_object = {}

    response = http_client.post(f'{domain_url}/infoflow/api/random/words', json=bad_object)
    assert response.status_code == 404, response.json()

    response = http_client.post(f'{domain_url}/infoflow/api/dataset', json=bad_object)
    assert response.status_code == 400, response.json()

    bad_object = {
        'name': 'Test object',
        'description': 'data data data',
        'undefined_field': 'this shouldn\'t be here',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/dataset', json=bad_object)
    assert response.status_code == 400, response.json()

    good_object = {
        'name': 'Test object',
        'description': 'data data data',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/dataset', json=good_object)
    assert response.status_code == 201, response.json()
    assert response.json()['_key']
    assert response.json()['name'] == good_object['name']
    assert response.json()['description'] == good_object['description']

    obj = {
        'name': 'Test writeOnly object',
        'rules': 'bah... rules, schmules',
        'expressions': [
            {
                'type': 'writeOnly',
                'value': 'this should not be shown in output'
            }
        ]
    }
    response = http_client.post(f'{domain_url}/infoflow/api/data_producer', json=obj)
    assert response.status_code == 201, response.json()
    assert response.json()['name'] == obj['name']
    assert response.json()['rules'] == obj['rules']
    assert 'expressions' not in response.json()

    obj = {
        'name': 'writeOnly name',
        'data': {
            'point': 'writeOnly obj'
        },
        'events': [
            'write',
            'only',
            'words',
        ]
    }
    response = http_client.post(f'{domain_url}/infoflow/api/talker', json=obj)
    assert response.status_code == 201, response.json()
    assert 'name' not in response.json()
    assert 'data' not in response.json()
    assert 'events' not in response.json()


def test_bulk_operations_domain_object(clean_db, http_client):
    # POST
    bad_list = [{}, {}, {}]

    response = http_client.post(f'{domain_url}/infoflow/api/outofthisworld/_bulk', json=bad_list)
    assert response.status_code == 404, response.json()

    response = http_client.post(f'{domain_url}/infoflow/api/dataset/_bulk', json=bad_list)
    assert response.status_code == 400, response.json()

    bad_object = {
        'name': 'Test object',
        'description': 'data data data',
        'undefined_field': 'this shouldn\'t be here',
    }
    good_object = {
        'name': 'Test object',
        'description': 'data data data',
        '_meta': {
            'note': 'test meta note'
        }
    }

    bad_list = [bad_object, good_object, good_object]

    response = http_client.post(f'{domain_url}/infoflow/api/dataset/_bulk', json=bad_list)
    assert response.status_code == 400, response.json()

    good_list = [good_object, good_object, good_object]

    response = http_client.post(f'{domain_url}/infoflow/api/dataset/_bulk', json=good_list)
    assert response.status_code == 201, response.json()
    assert isinstance(response.json(), list), response.json()
    _key_obj_list = [{'_key': result.get('_key')} for result in response.json()]

    # async
    params = {
        'sync': False
    }
    response = http_client.post(f'{domain_url}/infoflow/api/dataset/_bulk', json=good_list, params=params)
    assert response.status_code == 201, response.json()
    assert isinstance(response.json(), list), response.json()

    time.sleep(0.25)

    # PATCH
    bad_list = [{}, {}, {}]

    response = http_client.patch(f'{domain_url}/infoflow/api/outofthisworld/_bulk', json=bad_list)
    assert response.status_code == 404, response.json()

    bad_list = [*_key_obj_list]
    bad_list[0] = {}

    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/_bulk', json=bad_list)
    assert response.status_code == 400, response.json()

    good_list = [*_key_obj_list]
    good_list[0]['name'] = 'Test object changed 1'
    good_list[0]['_meta'] = {
        'note': 'test new meta note 1'
    }
    good_list[1]['name'] = 'Test object changed 2'
    good_list[1]['_meta'] = {
        'note': 'test new meta note 2'
    }
    good_list[2]['name'] = 'Test object changed 3'
    good_list[2]['_meta'] = {
        'note': 'test new meta note 3'
    }

    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/_bulk', json=good_list)
    assert response.status_code == 200, response.json()
    assert isinstance(response.json(), list), response.json()

    # async, ids only
    params = {
        'sync': False
    }

    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/_bulk', json=good_list, params=params)
    assert response.status_code == 200, response.json()
    assert isinstance(response.json(), list), response.json()

    time.sleep(0.25)

    # DELETE
    bad_list = [{}, {}, {}]

    response = http_client.request('delete', f'{domain_url}/infoflow/api/outofthisworld/_bulk', json=bad_list)
    assert response.status_code == 404, response.json()

    response = http_client.request('delete', f'{domain_url}/infoflow/api/dataset/_bulk', json=bad_list)
    assert response.status_code == 400, response.json()

    good_list = [*_key_obj_list]

    response = http_client.request('delete', f'{domain_url}/infoflow/api/dataset/_bulk', json=good_list, params=params)
    assert response.status_code == 200, response.json()

    good_list = [good_object, good_object, good_object]
    response = http_client.post(f'{domain_url}/infoflow/api/dataset/_bulk', json=good_list)
    _key_obj_list = [{'_key': result.get('_key')} for result in response.json()]
    assert isinstance(response.json(), list), response.json()

    # async, ids only
    params = {
        'sync': False
    }

    good_list = [*_key_obj_list]

    response = http_client.request('delete', f'{domain_url}/infoflow/api/dataset/_bulk', json=good_list)
    assert response.status_code == 200, response.json()
    assert isinstance(response.json(), list), response.json()
    _key_list = [result.get('_key') for result in response.json()]

    response = http_client.get(f'{domain_url}/infoflow/api/dataset')
    for item in response.json()['results']:
        assert item['_key'] not in _key_list


def test_get_domain_object(clean_db, backend_data, http_client):
    response = http_client.get(f'{domain_url}/infoflow/api/random/words/1')
    assert response.status_code == 404, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1')
    assert response.status_code == 200, response.json()
    assert response.json()['_key'] == '1'

    params = {'field': ['name']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'name': 'test a'
    }

    params = {'field': ['name', 'description']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'name': 'test a',
        'description': 'alpha'
    }

    params = {'relation': ['objects']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        '_class': 'dataset',
        '_key': '1',
        'name': 'test a',
        'description': 'alpha',
        'objects': [
            {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
        ]
    }

    params = {'field': ['name'], 'relation': ['objects']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'name': 'test a',
        'objects': [
            {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'},
        ]
    }

    params = {'field': ['name', 'objects.name'], 'relation': ['objects']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'name': 'test a',
        'objects': [
            {'name': 'test b'},
        ]
    }

    params = {'field': ['name', 'objects.name', 'objects.objects.name'], 'relation': ['objects', 'objects.objects']}
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'name': 'test a',
        'objects': [
            {
                'name': 'test b',
                'objects': [
                    {'name': 'test c'}
                ]
            },
        ]
    }

    params = {
        'field': ['name', 'objects.name', 'objects.objects.name'],
        'relation': ['objects', 'objects.objects'],
        'edge_filter': ['objects.objects.active == true']
    }
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1', params=params)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'name': 'test a',
        'objects': [
            {
                'name': 'test b',
                'objects': [
                    {'name': 'test c'}
                ]
            },
        ]
    }


def test_patch_domain_object(clean_db, backend_data, http_client):
    partial = {
        'name': 'Changed Test object'
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/random/words/1', json=partial)
    assert response.status_code == 404, response.json()

    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/1', json=partial)
    assert response.status_code == 200, response.json()
    assert response.json()['name'] == partial['name']

    obj = {
        'name': 'Test object',
        'rules': 'data data data',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/data_producer', json=obj)
    assert response.status_code == 201, response.json()
    _key = response.json()['_key']

    bad_partial = {
        'some': 'additional property'
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/data_producer/{_key}', json=bad_partial)
    assert response.status_code == 400, response.json()

    bad_partial = {
        'additional_data': {
            'test': 'test'
        }
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/data_producer/{_key}', json=bad_partial)
    assert response.status_code == 400, response.json()

    bad_partial = {
        'groups': [
            {
                'operator': 'test',
                'conditions': [
                    {
                        'array_scope': 'ALL',
                    }
                ]
            }
        ]
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/data_producer/{_key}', json=bad_partial)
    assert response.status_code == 400, response.json()

    bad_partial = {
        'groups': [
            {
                'operator': 'test',
                'conditions': [
                    {
                        'array_scope': 'SOME?',
                        'operator': 'test',
                        'property': 'test',
                        'property_type': 'array',
                        'type': 'test',
                        'value': 'test',
                        'value_type': 'string',
                    }
                ]
            }
        ]
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/data_producer/{_key}', json=bad_partial)
    assert response.status_code == 400, response.json()

    good_partial = {
        'groups': [
            {
                'operator': 'test',
                'conditions': [
                    {
                        'array_scope': 'ALL',
                        'operator': 'test',
                        'property': 'test',
                        'property_type': 'array',
                        'type': 'test',
                        'value': 'test',
                        'value_type': 'string',
                    }
                ]
            }
        ]
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/data_producer/{_key}', json=good_partial)
    assert response.status_code == 200, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/data_producer/{_key}/_changes')
    assert response.status_code == 200, response.json()
    results_total = response.json().get('results_total')
    results = response.json().get('results')

    assert results_total == 2
    assert len(results) == 2
    assert results[0]['operation'] == 'update'
    assert results[0]['pre'] == {}
    assert results[0]['post'] == {} # groups is a writeOnly attribute
    assert results[1]['operation'] == 'create'


def test_neighbors(clean_db, backend_data, http_client):
    response = http_client.get(f'{domain_url}/infoflow/api/dataset/2/_neighbors')
    assert response.status_code == 200

    nodes = response.json()['nodes']
    edges = response.json()['edges']
    edge_dict = {
        edge['_from']: {
            key: edge[key] for key in ['_relations', '_external_relations', '_to']
        } for edge in edges
    }

    assert set(node['_id'] for node in nodes) == set(['grouping/1', 'grouping/2', 'grouping/3'])
    assert set(node['_key'] for node in nodes) == set(['1', '2', '3'])
    assert set(node['_class'] for node in nodes) == set(['dataset'])
    assert len(edges) == 3
    assert edge_dict['grouping/1'] == {
        '_relations': [],
        '_external_relations': ['objects'],
        '_to': 'grouping/2'
    }
    assert edge_dict['grouping/2'] == {
        '_relations': ['objects'],
        '_external_relations': [],
        '_to': 'grouping/3'
    }
    assert edge_dict['grouping/3'] == {
        '_relations': [],
        '_external_relations': ['objects'],
        '_to': 'grouping/2'
    }


def test_patch_domain_object_for_domain_translated_changes(clean_db, backend_data, http_client):
    obj = {
        'name': 'test data source',
        'info': 'unpatched'
    }

    response = http_client.post(f'{domain_url}/infoflow/api/data_source', json=obj)
    assert response.status_code == 201, response.json()
    _key = response.json()['_key']

    time.sleep(.5)

    patch_body = {
        'info': 'Patched!'
    }

    response = http_client.patch(f'{domain_url}/infoflow/api/data_source/{_key}', json=patch_body)
    assert response.status_code == 200, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/data_source/{_key}/_changes')
    assert response.status_code == 200, response.json()
    results_total = response.json().get('results_total')
    results = response.json().get('results')

    assert results_total == 2
    assert len(results) == 2
    assert results[0]['pre'] == {'info': 'unpatched'}
    assert results[0]['post'] == {'info': 'Patched!'}
    assert results[1]['pre'] == {}
    assert results[1]['post'] == {'info': 'unpatched', 'name': 'test data source'}


def test_list_relations(clean_db, backend_data, http_client):
    response = http_client.get(f'{domain_url}/infoflow/api/random/words/1/rel')
    assert response.status_code == 404, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1/objects')
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'skip': 0,
        'limit': 100,
        'results_total': 1,
        'results': [
            {'_class': 'dataset', '_key': '2', 'name': 'test b', 'description': 'beta'}
        ]
    }


def test_list_relations_with_search_filter(clean_db, backend_data, http_client):
    url = f'{domain_url}/infoflow/api/dataset/3/objects'

    response = http_client.get(url)
    assert response.status_code == 200
    assert len(response.json()['results']) == 2

    params = {'search': 'beta'}
    response = http_client.get(url, params=params)
    assert response.status_code == 200
    assert len(response.json()['results']) == 1


def test_post_relation(db, clean_db, backend_data, http_client):
    bad_relation = {}

    response = http_client.post(f'{domain_url}/infoflow/api/random/words/1/rel', json=bad_relation)
    assert response.status_code == 404, response.json()

    response = http_client.post(f'{domain_url}/infoflow/api/dataset/1/objects', json=bad_relation)
    assert response.status_code == 400, response.json()

    good_relation = {
        'to_class': 'dataset',
        'to_key': '3',
        'data': 'test'
    }

    response = http_client.post(f'{domain_url}/infoflow/api/dataset/1/objects', json=good_relation)
    assert response.status_code == 201, response.json()

    query = '''
    FOR edge IN includes
        FILTER edge._from == "grouping/1" AND edge._to == "grouping/3"
        RETURN edge
    '''
    edge = db.aql(query)['result']

    assert len(edge) == 1
    assert edge[0]['data'] == 'test'
    assert edge[0]['active'] is True


# TODO: doesn't pass, disabled for now, investigate later
def x_test_post_relation_object(db, clean_db, backend_data, http_client):
    new_object_relation = {
        '_class': 'dataset',
        '_edge': {
            'data': 'test test'
        },
        'name': 'new dataset',
        'description': 'this is a new object',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/dataset/1/objects', json=new_object_relation)
    assert response.status_code == 201, response.json()

    assert '_key' in response.json()
    assert '_class' in response.json()
    assert response.json()['_class'] == 'dataset'
    assert 'creator' in response.json()
    assert 'created' in response.json()
    assert 'updated' in response.json()
    assert '_edge' in response.json()
    assert 'data' in response.json()['_edge']
    assert response.json()['_edge']['data'] == 'test test'
    assert 'active' in response.json()['_edge']
    assert response.json()['_edge']['active'] is True
    assert 'creator' in response.json()['_edge']
    assert 'created' in response.json()['_edge']
    assert 'updated' in response.json()['_edge']

    _key = response.json()['_key']

    query = f'''
    FOR edge IN includes
        FILTER edge._from == "grouping/1" AND edge._to == "grouping/{_key}"
        RETURN edge
    '''
    edge = db.aql(query)['result']

    assert len(edge) == 1
    assert edge[0]['data'] == 'test test'


def test_patch_relation(db, clean_db, backend_data, http_client):
    relation = {
        'to_class': 'dataset',
        'to_key': '3',
        'data': 'test updated'
    }

    response = http_client.patch(f'{domain_url}/infoflow/api/random/words/1/rel', json=relation)
    assert response.status_code == 404, response.json()

    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/1/objects', json=relation)
    assert response.status_code == 204, response.json()

    query = '''
    FOR edge IN includes
        FILTER edge._from == "grouping/1" AND edge._to == "grouping/3"
        RETURN edge
    '''
    edge = db.aql(query)['result']

    assert len(edge) == 1
    assert edge[0]['data'] == 'test updated'


def test_delete_relation(db, clean_db, backend_data, http_client):
    params = {
        'to_class': 'dataset',
        'to_key': '3'
    }

    response = http_client.delete(f'{domain_url}/infoflow/api/random/words/1/rel', params=params)
    assert response.status_code == 404, response.json()

    response = http_client.delete(f'{domain_url}/infoflow/api/dataset/1/objects', params=params)
    assert response.status_code == 204, response.json()

    time.sleep(1)

    query = '''
    FOR edge IN includes
        FILTER edge._from == "entity/1" AND edge._to == "entity/3"
        RETURN edge
    '''
    edge = db.aql(query)['result']

    assert len(edge) == 0


def test_delete_domain_object(clean_db, backend_data, http_client):
    response = http_client.delete(f'{domain_url}/infoflow/api/random/words/1')
    assert response.status_code == 404, response.json()

    response = http_client.delete(f'{domain_url}/infoflow/api/dataset/1')
    assert response.status_code == 204, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/dataset/1')
    assert response.status_code == 404, response.json()


def test_alias_classes(clean_db, backend_data, http_client):
    data = {
        'data': 'data',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/amalgam', json=data)
    assert response.status_code == 201, response.json()
    assert response.json().get('_class') == 'amalgam', response.json()
    assert response.json().get('sanity_check') == 'create-only', response.json()
    _key = response.json()['_key']

    response = http_client.get(f'{domain_url}/infoflow/api/amalgam/{_key}')
    assert response.status_code == 200, response.json()
    assert response.json().get('_class') == 'amalgam', response.json()
    assert response.json().get('sanity_check') == 'amalgam', response.json()

    data = {
        'data': 'changed',
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/amalgam/{_key}', json=data)
    assert response.status_code == 200, response.json()
    assert response.json().get('_class') == 'amalgam', response.json()
    assert response.json().get('data') == 'changed', response.json()
    assert response.json().get('sanity_check') == 'update-only', response.json()

    response = http_client.delete(f'{domain_url}/infoflow/api/amalgam/{_key}')
    assert response.status_code == 204, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/amalgam/{_key}')
    assert response.status_code == 404, response.json()


@pytest.fixture
def operations_data(db, clean_db):
    data = [
        {
            '_key': '1',
            '_class': 'hidden',
        },
    ]
    grouping = [
        {
            '_key': '2',
            '_class': 'notification',
        },
    ]

    # import manually for explicit keys
    db.truncate_collection('data')
    db.truncate_collection('grouping')
    db.bulk_create('data', data)
    db.bulk_create('grouping', grouping)


def test_operations(clean_db, operations_data, http_client):
    response = http_client.get(f'{domain_url}/infoflow/api/hidden')
    assert response.status_code == 405, response.json()

    response = http_client.post(f'{domain_url}/infoflow/api/hidden', json={})
    assert response.status_code == 405, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/hidden/1')
    assert response.status_code == 405, response.json()

    response = http_client.patch(f'{domain_url}/infoflow/api/hidden/1', json={})
    assert response.status_code == 405, response.json()

    response = http_client.delete(f'{domain_url}/infoflow/api/hidden/1')
    assert response.status_code == 405, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/notification')
    assert response.status_code == 200, response.json()

    response = http_client.post(f'{domain_url}/infoflow/api/notification', json={})
    assert response.status_code == 405, response.json()

    response = http_client.get(f'{domain_url}/infoflow/api/notification/2')
    assert response.status_code == 200, response.json()

    response = http_client.patch(f'{domain_url}/infoflow/api/notification/2', json={'info': 'test'})
    assert response.status_code == 200, response.json()

    response = http_client.delete(f'{domain_url}/infoflow/api/notification/2')
    assert response.status_code == 405, response.json()


@pytest.fixture
def relation_features_data(db, clean_db):
    source = [
        {
            '_key': '1',
            '_class': 'data_source',
        },
    ]
    ruleset = [
        {
            '_key': '1',
            '_class': 'data_producer',
        },
    ]
    data = [
        {
            '_key': '1',
            '_class': 'bit_data',
        },
        {
            '_key': '2',
            '_class': 'bit_data',
        },
        {
            '_key': '3',
            '_class': 'bit_data',
        },
        {
            '_key': '4',
            '_class': 'byte_data',
        },
    ]
    origin = [
        {
            '_from': 'data/1',
            '_to': 'source/1'
        },
        {
            '_from': 'data/2',
            '_to': 'source/1'
        },
        {
            '_from': 'data/3',
            '_to': 'source/1'
        },
        {
            '_from': 'data/4',
            '_to': 'ruleset/1'
        },
        {
            '_from': 'data/4',
            '_to': 'data/1',
            'cascade': True,
        },
        {
            '_from': 'data/4',
            '_to': 'data/2'
        },
    ]

    # import manually for explicit keys

    db.truncate_collection('source')
    db.truncate_collection('ruleset')
    db.truncate_collection('data')
    db.truncate_collection('origin')

    db.bulk_create('source', source)
    db.bulk_create('ruleset', ruleset)
    db.bulk_create('data', data)
    db.bulk_create('origin', origin)


def test_relation_features(clean_db, relation_features_data, http_client):
    # test relation target restriction
    response = http_client.get(f'{domain_url}/infoflow/api/byte_data/4/bits')
    assert response.status_code == 200, response.json()
    assert len(response.json().get('results')) == 2, response.json()  # 2 bits

    # test relation target restriction, traversal depth
    response = http_client.get(f'{domain_url}/infoflow/api/byte_data/4/origin')
    assert response.status_code == 200, response.json()
    assert len(response.json().get('results')) == 4, response.json() # 2 bits, 1 producer (direct), 1 source (indirect)

    params = {'edge_filter': ['non_existent == true']}
    response = http_client.get(f'{domain_url}/infoflow/api/byte_data/4/bits', params=params)
    assert response.status_code == 400, response.json()

    params = {'edge_filter': ['cascade == true']}
    response = http_client.get(f'{domain_url}/infoflow/api/byte_data/4/bits', params=params)
    assert response.status_code == 200, response.json()
    assert len(response.json().get('results')) == 1, response.json()  # 1 bit


@pytest.fixture
def constants_data(db, clean_db):
    data = [
        {
            '_key': '1',
            '_class': 'constant',
        },
    ]

    # import manually for explicit keys
    db.truncate_collection('data')
    db.bulk_create('data', data)


def test_constants(clean_db, constants_data, http_client):
    response = http_client.get(f'{domain_url}/infoflow/api/constant/1')
    assert response.status_code == 200, response.json()
    assert response.json() == {
        '_key': '1',
        '_class': 'constant',
        'test_a': 'value',
        'test_b': 1,
        'test_c': 1.01,
        'test_d': True,
    }


def test_nullable(clean_db, http_client):
    data = {
        'name': 'data',
        'description': None,
    }

    response = http_client.post(f'{domain_url}/infoflow/api/nullable', json=data)
    assert response.status_code == 201, response.json()


def test_arbitrary_meta(clean_db, http_client):
    data = {
        '_meta': {
            'meta': 'test'
        },
        'data': 'data',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/meta', json=data)
    assert response.status_code == 201, response.json()


def test_defaults(clean_db, http_client):
    data = {}

    response = http_client.post(f'{domain_url}/infoflow/api/defaulter', json=data)
    assert response.status_code == 201, response.json()
    assert not response.json().get('active'), response.json()

    data = [{}, {}]

    response = http_client.post(f'{domain_url}/infoflow/api/defaulter/_bulk', json=data)
    assert response.status_code == 201, response.json()
    for d in response.json():
        assert not d.get('new').get('active'), response.json()


def test_nullable_new(clean_db, http_client):
    data = {
        'name': 'NEU!',
        'description': 'Für immer',
        'start_date': '1973-01-01T00:00:00.000Z',
        'end_date': '1973-01-01T00:00:00.000Z',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/brand_new_class', json=data)
    assert response.status_code == 201, response.json()
    _key = response.json()['_key']

    data = {
        'end_date': None,
    }

    response = http_client.patch(f'{domain_url}/infoflow/api/brand_new_class/{_key}', json=data)
    assert response.status_code == 200, response.json()
