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
            'data': 123,
            'extra': 'An alpha wildcard appears!',
            'test.me': 'A wrench in the benedict machinery'
        },
        {
            '_key': '2',
            '_class': 'dataset',
            '_index': 'test b beta',
            'label': 'test b',
            'data': 456,
            'extra': 'A beta wildcard appears!'
        },
        {
            '_key': '3',
            '_class': 'dataset',
            '_index': 'test c gamma',
            'label': 'test c',
            'data': 789,
            'extra': 'A gamma wildcard appears!'
        },
    ]

    edges = [
        {
            '_key': '1',
            '_from': 'grouping/1',
            '_to': 'grouping/2',
            'active': True
        },
        {
            '_key': '2',
            '_from': 'grouping/2',
            '_to': 'grouping/3',
            'active': True
        },
    ]

    # import manually for explicit keys
    db.bulk_create('grouping', nodes)
    db.bulk_create('includes', edges)

    return nodes, edges


def test_empty_domain(clean_db, http_client):
    # run simple query
    query = '''{
        Dataset(_key: 1) {
            name
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'Dataset': None
        }
    }

    # run another simple query
    query = '''{
        DatasetList {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 0,
                'results': []
            }
        }
    }


def test_simple_queries(clean_db, backend_data, http_client):
    # confirm data is imported and accessible
    query = '''{
        Dataset(_key: 1) {
            name
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'Dataset': {
                'name': 'test a'
            }
        }
    }

    # run list query and use bad skip, limit
    query = '''{
        DatasetList(skip: "skvip", limit: "love") {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    # run list query and use skip, limit
    query = '''{
        DatasetList(skip: 2, limit: 1) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 3,
                'results': [
                    {'name': 'test c'}
                ]
            }
        }
    }

    # run list query and use bad sort
    query = '''{
        DatasetList(sort: ["bad"]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    # run list query and use sort
    query = '''{
        DatasetList(sort: ["_class", "-name"]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 3,
                'results': [
                    {'name': 'test c'},
                    {'name': 'test b'},
                    {'name': 'test a'},
                ]
            }
        }
    }

    # run list query and use bad filter
    query = '''{
        DatasetList(filter: ["flump == \\"test b\\""]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    # run list query and use filter
    query = '''{
        DatasetList(filter: ["name == \\"test b\\""]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 1,
                'results': [
                    {'name': 'test b'}
                ]
            }
        }
    }

    # run list query and use multiple filters
    query = '''{
        DatasetList(filter: ["name LIKE \\"test%\\"", "name LIKE \\"%b\\""]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 1,
                'results': [
                    {'name': 'test b'}
                ]
            }
        }
    }

    # run list query and use filter
    query = '''{
        DatasetList(filter: ["name == \\"nonexistent\\""]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 0,
                'results': []
            }
        }
    }

    # run list query and use filter
    # please ignore description being a number
    query = '''{
        DatasetList(filter: ["description > 999"]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 0,
                'results': []
            }
        }
    }

    # run list query and use filter
    # please ignore description being a number
    query = '''{
        DatasetList(filter: ["description >= 456"]) {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 2,
                'results': [
                    {'name': 'test b'},
                    {'name': 'test c'}
                ]
            }
        }
    }

    # run list query and use search
    query = '''{
        DatasetList(search: "test") {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 3,
                'results': [
                    {'name': 'test a'},
                    {'name': 'test b'},
                    {'name': 'test c'}
                ]
            }
        }
    }

    # run list query and use search
    query = '''{
        DatasetList(search: "alpha") {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 1,
                'results': [
                    {'name': 'test a'}
                ]
            }
        }
    }

    # run list query and use search
    query = '''{
        DatasetList(search: "nonexistent") {
            results_total
            results {
                name
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList':  {
                'results_total': 0,
                'results': []
            }
        }
    }


def test_wildcard_queries(clean_db, backend_data, http_client):
    # confirm _all works with nested queries
    # please ignore description being a number
    query = '''{
        Dataset(_key: 1) {
            _all
            objects {
                results {
                    ...on Dataset {
                        _all
                    }
                }
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'Dataset': {
                '__typename': 'Dataset',
                '_key': '1',
                'name': 'test a',
                'description': 123,
                'extra': 'An alpha wildcard appears!',
                'test.me': 'A wrench in the benedict machinery',
                'objects': {
                    'results': [
                        {
                            '__typename': 'Dataset',
                            '_key': '2',
                            '_edge': {
                                'active': True
                            },
                            'name': 'test b',
                            'description': 456,
                            'extra': 'A beta wildcard appears!'
                        }
                    ]
                }
            }
        }
    }

    # confirm _all works with multiple results
    # please ignore description being a number
    query = '''{
        DatasetList(skip: 1, limit: 2) {
            results_total
            results {
                _all
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DatasetList': {
                'results_total': 3,
                'results': [
                    {
                        '__typename': 'Dataset',
                        '_key': '2',
                        'name': 'test b',
                        'description': 456,
                        'extra': 'A beta wildcard appears!'
                    },
                    {
                        '__typename': 'Dataset',
                        '_key': '3',
                        'name': 'test c',
                        'description': 789,
                        'extra': 'A gamma wildcard appears!'
                    }
                ]
            }
        }
    }


def test_relation_queries(clean_db, backend_data, http_client):
    query = '''
    query NestedDatasetQuery {
        Dataset(_key: 1) {
            name
            objects {
                results {
                    ...on Dataset {
                        name
                        _edge {
                            active
                        }
                        objects {
                            results {
                                ...on Dataset {
                                    name
                                    _edge {
                                        active
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'Dataset': {
                'name': 'test a',
                'objects': {
                    'results': [
                        {
                            'name': 'test b',
                            '_edge': {
                                'active': True
                            },
                            'objects': {
                                'results': [
                                    {
                                        'name': 'test c',
                                        '_edge': {
                                            'active': True
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }


def test_mutation_queries(clean_db, backend_data, http_client):
    # run mutation, invalid timeref
    query = '''
    mutation TestDateTimeInValidation {
        createDataSource(input: {name: "creo mutado!", info: "data", timeref: "123"}) {
            _key
            name
            info
            timeref
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    # run mutation to add a new object
    query = '''
    mutation CreateDataSourceTest {
        createDataSource(input: {name: "creo mutado!", info: "data", timeref: "2021-01-01T00:00:00.000000Z"}) {
            _key
            name
            info
            timeref
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text

    data = response.json()
    _key = data['data']['createDataSource'].pop('_key')
    assert data == {
        'data': {
            'createDataSource': {
                'name': 'creo mutado!',
                'info': 'data',
                'timeref': '2021-01-01T00:00:00.000000Z',
            }
        }
    }

    # run mutation to update again
    query = f'''
    mutation UpdateDataSourceTest {{
        updateDataSource(_key: {_key}, input: {{name: "mutado mutador!"}}) {{
            _key
            name
        }}
    }}
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'updateDataSource': {
                '_key': _key,
                'name': 'mutado mutador!'
            }
        }
    }

    # run mutation to delete object
    query = f'''
    mutation DeleteDataSourceTest {{
        deleteDataSource(_key: {_key})
    }}
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'deleteDataSource': True
        }
    }

    # confirm object is gone
    query = f'''{{
        DataSource(_key: {_key}) {{
            name
        }}
    }}'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'DataSource': None
        }
    }

    # add an object with writeOnly: true
    query = '''
    mutation CreateDataProducer {
        createDataProducer(input: {
                name: "Test writeOnly object",
                rules: "made to be broken",
                expressions: [
                    {
                        type: "writeOnly",
                        value: "this should not be shown in output"
                    }
                ]
            }) {
            _key
            name
            rules
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    data = response.json()
    _key = data['data']['createDataProducer'].pop('_key')
    assert response.status_code == 200, response.text
    assert data == {
        'data': {
            'createDataProducer': {
                'name': 'Test writeOnly object',
                'rules': 'made to be broken',
            }
        }
    }

    # expressions should not be available
    query = f'''{{
        DataProducer(_key: {_key}) {{
            expressions {{
                type
                value
            }}
        }}
    }}'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text


def test_nested_mutation_queries(clean_db, backend_data, http_client):
    # run mutation to add a new object
    query = '''
    mutation CreateNestedData {
        createDataSource(input: {
            name: "Source of Uncertainty",
            info: "???"
            tags: ["noise", "random", "sample and hold"],
            connection_data: { data: "banana cables" },
            examples: [
                { data: "0.969 4.080 3.478 4.833 2.645" },
                { data: "1 0 1 0 0 0 1 0 1 1 0" }
            ]
        }) {
            _key
            name
            info
            tags
            connection_data { data }
            examples { data }
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text

    data = response.json()
    _key = data['data']['createDataSource'].pop('_key')
    assert data == {
        'data': {
            'createDataSource': {
                'name': 'Source of Uncertainty',
                'info': '???',
                'tags': ['noise', 'random', 'sample and hold'],
                'connection_data': { 'data': 'banana cables' },
                'examples': [
                    { 'data': '0.969 4.080 3.478 4.833 2.645' },
                    { 'data': '1 0 1 0 0 0 1 0 1 1 0' }
                ]
            }
        }
    }

    # run mutation to update again
    query = f'''
    mutation UpdateNestedData {{
        updateDataSource(_key: {_key}, input: {{
            tags: ["uncertainty"],
            connection_data: {{ data: "test" }},
            examples: [
                {{ data: "none" }}
            ]
        }}) {{
            tags
            connection_data {{ data }}
            examples {{ data }}
        }}
    }}
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'updateDataSource': {
                'tags': ['uncertainty'],
                'connection_data': { 'data': 'test' },
                'examples': [
                    { 'data': 'none' },
                ]
            }
        }
    }


def test_edge_mutation_queries(clean_db, backend_data, http_client):
    # add ByteData
    query = '''
    mutation CreateByteData {
        createByteData(input: {data: "data"}) {
            _key
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text

    data = response.json()
    ds_key = '3'
    bd_key = data['data']['createByteData']['_key']

    # run mutation to add relation
    query = f'''
    mutation AddRelation {{
        attachDatasetObjectsRelation(from: {{type: "Dataset", _key: {ds_key}}}, to: {{type: "ByteData", _key: {bd_key}}})
    }}
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'attachDatasetObjectsRelation': True
        }
    }

    # confirm relation was created
    query = '''
    {
        Dataset(_key: 3) {
            objects {
                results {
                    ...on ByteData {
                        data
                    }
                }
            }
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'Dataset': {
                'objects': {
                    'results': [
                        {'data': 'data'}
                    ]
                }
            }
        }
    }

    # run mutation to remove relation
    query = f'''
    mutation RemoveRelation {{
        detachDatasetObjectsRelation(from: {{type: "Dataset", _key: {ds_key}}}, to: {{type: "ByteData", _key: {bd_key}}})
    }}
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'detachDatasetObjectsRelation': True
        }
    }

    # confirm relation is gone
    query = '''
    {
        Dataset(_key: 3) {
            objects {
                results {
                    ...on ByteData {
                        data
                    }
                }
            }
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'Dataset': {
                'objects': {
                    'results': [
                    ]
                }
            }
        }
    }


def test_edge_mutation_add_relation(clean_db, backend_data, http_client):
    # run mutation to add relation
    query = '''
    mutation AddRelation {
        createDatasetObjectsRelatedDataset(
            _key: 1,
            input: {
                name: "new dataset",
                description: "this is a new dataset"
            },
            _edge: {
                active: false
            }) {
                name
                description
                _edge {
                    active
                }
            }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'createDatasetObjectsRelatedDataset': {
                'name': 'new dataset',
                'description': 'this is a new dataset',
                '_edge': {
                    'active': False
                }
            }
        }
    }


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
    query = '''{
        HiddenList {
            results {
                _key
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    query = '''{
        Hidden(_key: 1) {
            name
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    query = '''
    mutation CreateHidden {
        createHidden {
            _key
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    query = '''
    mutation UpdateHidden {
        updateHidden(_key: 1) {
            _key
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    query = '''
    mutation DeleteHidden {
        deleteHidden(_key: 1) {
            _key
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    query = '''{
        NotificationList {
            results {
                _key
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text

    query = '''{
        Notification(_key: 2) {
            _key
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text

    query = '''
    mutation CreateNotification {
        createNotification {
            _key
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text

    query = '''
    mutation UpdateNotification {
        updateNotification(_key: 2) {
            _key
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text

    query = '''
    mutation DeleteNotification {
        deleteNotification(_key: 2) {
            _key
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 400, response.text


@pytest.fixture
def relation_features_data(db, clean_db):
    data = [
        {
            '_key': '1',
            '_class': 'bit_data',
        },
        {
            '_key': '2',
            '_class': 'bit_data',
            '_index': 'abc'
        },
        {
            '_key': '3',
            '_class': 'bit_data',
            '_index': 'cfg'
        },
        {
            '_key': '4',
            '_class': 'byte_data',
        },
        {
            '_key': '5',
            '_class': 'byte_data',
        },
    ]
    origin = [
        {
            '_from': 'data/4',
            '_to': 'data/1',
            'cascade': True,
        },
        {
            '_from': 'data/5',
            '_to': 'data/2'
        },
        {
            '_from': 'data/5',
            '_to': 'data/3'
        },
    ]

    # import manually for explicit keys
    db.truncate_collection('data')
    db.truncate_collection('origin')
    db.bulk_create('data', data)
    db.bulk_create('origin', origin)


def test_relation_edge_filter(clean_db, relation_features_data, http_client):
    query = '''{
        ByteData(_key: 4) {
            bits(edge_filter: ["cascade == true"]) {
                results_total
                results {
                    _key
                    _edge {
                        cascade
                    }
                }
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'ByteData': {
                'bits': {
                    'results_total': 1,
                    'results': [
                        {
                            '_key': '1',
                            '_edge': {
                                'cascade': True,
                            }
                        }
                    ]
                }
            }
        }
    }


def test_relation_search_filter(clean_db, relation_features_data, http_client):
    query = '''{
        ByteData(_key: 5) {
            bits(search: "cfg") {
                results_total
                results {
                    _key
                }
            }
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'ByteData': {
                'bits': {
                    'results_total': 1,
                    'results': [
                        {
                            '_key': '3',
                        }
                    ]
                }
            }
        }
    }


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
    query = '''{
        Constant(_key: 1) {
            test_a
            test_b
            test_c
            test_d
        }
    }'''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text
    assert response.json() == {
        'data': {
            'Constant': {
                'test_a': 'value',
                'test_b': 1,
                'test_c': 1.01,
                'test_d': True,
            }
        }
    }


def test_defaults(clean_db, http_client):
    query = '''
    mutation CreateDefaulterTest {
        createDefaulter {
            _key
            active
        }
    }
    '''
    response = http_client.post(f'{domain_url}/infoflow/graphql', json={'query': query})
    assert response.status_code == 200, response.text

    data = response.json()
    _key = data['data']['createDefaulter'].pop('_key')
    assert data == {
        'data': {
            'createDefaulter': {
                'active': False,
            }
        }
    }
