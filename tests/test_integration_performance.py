
import pytest
import httpx

from tests.conftest import gateway_url


DATASETS = 100
CFACTOR = 3
YFACTOR = 5
IFACTOR = 8

COMMENTS = DATASETS * CFACTOR
BYTES = DATASETS * YFACTOR
BITS = BYTES * IFACTOR

SEARCH_RESULTS = 100


@pytest.fixture(scope='module')
def benchmark_data(db, clean_db):
    bit_data = [
        {
            '_key': f'{i}',
            '_class': 'bit_data',
            'created': '1970-01-01T00:00:00.000Z',
            'data': 'data ' * 128,
        }
        for i in range(BITS)
    ]
    db.bulk_create('data', bit_data, sync=True)

    byte_data = [
        {
            '_key': f'{BITS + i}',
            '_class': 'byte_data',
            'created': '1970-01-01T00:00:00.000Z',
            'data': 'data ' * 1024,
        }
        for i in range(BYTES)
    ]
    db.bulk_create('data', byte_data, sync=True)

    byte_bits = [
        {
            '_key': f'{i}',
            '_from': f'data/{BITS + (i % IFACTOR)}',
            '_to': f'data/{i}',
        }
        for i in range(BITS)
    ]
    db.bulk_create('origin', byte_bits, sync=True)

    datasets = [
        {
            '_key': f'{i}',
            '_class': 'dataset',
            'creator': 'TESTMAN!',
            'created': '1970-01-01T00:00:00.000Z',
            'updated': '1970-01-01T00:00:00.000Z',
            'label': f'dataset {i}',
            'data': f'This is dataset {i}' + ('blah ' * 100),
        }
        for i in range(DATASETS)
    ]
    db.bulk_create('grouping', datasets, sync=True)

    dataset_objs = [
        {
            '_key': f'{i}',
            '_from': f'grouping/{i % YFACTOR}',
            '_to': f'data/{BITS + i}',
        }
        for i in range(BYTES)
    ]
    db.bulk_create('includes', dataset_objs, sync=True)

    comments = [
        {
            '_key': f'{i}',
            '_class': 'comment',
            'creator': 'tester',
            'created': '1970-01-01T00:00:00.000Z',
            'updated': '1970-01-01T00:00:00.000Z',
            'data': 'lorem ipsum dolor sit amet ' * 40,
        } for i in range(COMMENTS)
    ]
    db.bulk_create('comment', comments, sync=True)

    comments_on = [
        {
            '_key': f'{i}',
            '_from': f'comment/{i}',
            '_to': f'grouping/{i % CFACTOR}',
        }
        for i in range(COMMENTS)
    ]
    db.bulk_create('comment_on', comments_on, sync=True)

    search_results = [
        {
            '_key': f'{DATASETS + i}',
            '_class': 'search_result',
            'creator': 'TESTMAN!',
            'created': '1970-01-01T00:00:00.000Z',
            'updated': '1970-01-01T00:00:00.000Z',
            'label': f'search_result {DATASETS + i}',
            'data': f'This is search_result {DATASETS + i}' + ('blah ' * 100),
        }
        for i in range(SEARCH_RESULTS)
    ]
    db.bulk_create('grouping', search_results, sync=True)


@pytest.fixture(scope='module')
def headers():
    credentials = {
        'username': 'testuser',
        'password': 'secret',
    }

    response = httpx.post(f'{gateway_url}/authly/api/auth/authenticate', json=credentials, verify=False)
    assert response.status_code == 200, response.text

    token = response.json().get('token')
    return {
        'Authorization': f'Bearer {token}'
    }


def xtest_get_health(benchmark_data, headers, http_client):
    response = http_client.get(f'{gateway_url}/health', headers=headers)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def test_get_domain_object(benchmark_data, headers, http_client):
    response = http_client.get(f'{gateway_url}/infoflow/api/dataset/0', headers=headers)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def test_list_domain_objects(benchmark_data, headers, http_client):
    response = http_client.get(f'{gateway_url}/infoflow/api/dataset', headers=headers)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def test_simple_graphql_query(benchmark_data, headers, http_client):
    query = '''
    query SimpleGraphQLQuery {
        Dataset(_key: 0) {
            creator
            created
            name
            description
        }
    }'''
    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': query}, headers=headers)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def test_heavy_graphql_query(benchmark_data, headers, http_client):
    query = '''
    query HeavyGraphQLQuery {
        DatasetList {
            results_total
            results {
                creator
                created
                name
                description
                objects {
                    results_total
                    results {
                        ...on ByteData {
                            data
                            bits {
                                results_total
                                results {
                                    data
                                }
                            }
                        }
                    }
                }
                comments {
                    results_total
                    results {
                        content
                    }
                }
            }
        }
    }'''
    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': query}, headers=headers, timeout=15)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def test_post_domain_object(benchmark_data, headers, http_client):
    obj = {
        'name': 'New test dataset',
        'description': 'blah blah blah ' * 20
    }

    response = http_client.post(f'{gateway_url}/infoflow/api/dataset', json=obj, headers=headers)
    assert response.status_code == 201, response.text
    # print(len(response.text))


def test_simple_graphql_mutation_query(benchmark_data, headers, http_client):
    query = '''
    mutation CreateDataset {
        createDataset(input: {
            name: "New test dataset",
            description: "blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah "
        }) {
            _key
            name
            description
        }
    }
    '''
    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': query}, headers=headers)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def xtest_nested_graphql_mutation_query(benchmark_data, headers, http_client):
    query = '''
    mutation CreateNestedDataset {
        createDataset(input: {
            name: "New test dataset",
            description: "blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah "
        }) {
            _key
            name
            description
        }
    }
    '''
    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': query}, headers=headers)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def test_access_rpc(benchmark_data, headers, http_client):
    response = http_client.get(f'{gateway_url}/infoflow/api/search_result', headers=headers)
    assert response.status_code == 200, response.text
    # print(len(response.text))


def test_simple_service_rpc(benchmark_data, headers, http_client):
    obj = {
        'name': 'Test object',
        'description': 'data data data',
    }

    response = http_client.post(f'{gateway_url}/infoflow/api/search_result', json=obj, headers=headers)
    assert response.status_code == 201, response.text
    # print(len(response.text))


def test_complex_service_rpc(benchmark_data, headers, http_client):
    obj = {
        'data': 'data data data',
    }

    response = http_client.post(f'{gateway_url}/infoflow/api/meta', json=obj, headers=headers)
    assert response.status_code == 201, response.text
    # print(len(response.text))
