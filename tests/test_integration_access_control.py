import io

import httpx

from tests.conftest import gateway_url
import tests.helpers.minio as minio_helpers


def get_headers(payload):
    response = httpx.post(f'{gateway_url}/authly/api/auth/authenticate', json=payload, verify=False)
    assert response.status_code == 200, response.text

    token = response.json().get('token')
    return {
        'Authorization': f'Bearer {token}'
    }


def test_domain(db, http_client):
    last_round = [
        {'_key': 'example_a'},
        {'_key': 'example_b'},
        {'_key': 'example_c'},
        {'_key': 'example_d'},
    ]
    db.bulk_delete('domain', last_round, old=False)

    headers = get_headers({
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    })

    data = {
        'label': 'Example A',
        'description': 'Description',
        'schema': '''
            a:
                description: Example
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }

    response = http_client.post(f'{gateway_url}/system/api/domain', headers=headers, json=data)
    assert response.status_code == 201, response.text

    _key = response.json().get('_key')

    response = http_client.get(f'{gateway_url}/system/api/domain', headers=headers)
    assert response.status_code == 200, response.text

    partial = {
        'label': 'Example changed!'
    }

    response = http_client.patch(f'{gateway_url}/system/api/domain/{_key}', headers=headers, json=partial)
    assert response.status_code == 200, response.text

    response = http_client.delete(f'{gateway_url}/system/api/domain/{_key}', headers=headers)
    assert response.status_code == 204, response.text

    headers = get_headers({
        'username': 'root',
        'password': 'secret',
    })

    data = {
        'label': 'Example B',
        'description': 'Description',
        'schema': '''
            a:
                description: Example
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }

    response = http_client.post(f'{gateway_url}/system/api/domain', headers=headers, json=data)
    assert response.status_code == 201, response.text

    _key = response.json().get('_key')

    response = http_client.get(f'{gateway_url}/system/api/domain', headers=headers)
    assert response.status_code == 200, response.text

    partial = {
        'label': 'Example changed!'
    }

    response = http_client.patch(f'{gateway_url}/system/api/domain/{_key}', headers=headers, json=partial)
    assert response.status_code == 200, response.text

    response = http_client.delete(f'{gateway_url}/system/api/domain/{_key}', headers=headers)
    assert response.status_code == 204, response.text

    headers = get_headers({
        'username': 'testuser',
        'password': 'secret',
    })

    data = {
        'label': 'Example C',
        'description': 'Description',
        'schema': '''
            a:
                description: Example
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }

    response = http_client.post(f'{gateway_url}/system/api/domain', headers=headers, json=data)
    assert response.status_code == 401, response.text

    _key = response.json().get('_key')

    response = http_client.get(f'{gateway_url}/system/api/domain', headers=headers)
    assert response.status_code == 200, response.text

    partial = {
        'label': 'Example changed!'
    }

    response = http_client.patch(f'{gateway_url}/system/api/domain/{_key}', headers=headers, json=partial)
    assert response.status_code == 401, response.text

    response = http_client.delete(f'{gateway_url}/system/api/domain/{_key}', headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'noman',
        'password': 'secret',
    })

    data = {
        'label': 'Example D',
        'description': 'Description',
        'schema': '''
            a:
                description: Example
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }

    response = http_client.post(f'{gateway_url}/system/api/domain', headers=headers, json=data)
    assert response.status_code == 401, response.text

    _key = response.json().get('_key')

    response = http_client.get(f'{gateway_url}/system/api/domain', headers=headers)
    assert response.status_code == 401, response.text

    partial = {
        'label': 'Example changed!'
    }

    response = http_client.patch(f'{gateway_url}/system/api/domain/{_key}', headers=headers, json=partial)
    assert response.status_code == 401, response.text

    response = http_client.delete(f'{gateway_url}/system/api/domain/{_key}', headers=headers)
    assert response.status_code == 401, response.text


def test_service(clean_db, http_client):
    headers = get_headers({
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    })

    response = http_client.get(f'{gateway_url}/system/api/service', headers=headers)
    assert response.status_code == 200, response.text

    data = {
        'name': 'Yet Another Service',
        'info': 'This is yet another service',
        'host': 'https://another-service:6002',
        'api': '/api'
    }

    response = http_client.post(f'{gateway_url}/system/api/service/register', headers=headers, json=data)
    assert response.status_code == 201, response.text

    response = http_client.delete(f'{gateway_url}/system/api/service/unregister/yet_another_service', headers=headers)
    assert response.status_code == 204, response.text

    response = http_client.get(f'{gateway_url}/system/api/service/test_service/api/health', headers=headers)
    assert response.status_code == 200, response.text

    headers = get_headers({
        'username': 'root',
        'password': 'secret',
    })

    response = http_client.get(f'{gateway_url}/system/api/service', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.post(f'{gateway_url}/system/api/service/register', headers=headers, json=data)
    assert response.status_code == 401, response.text

    response = http_client.delete(f'{gateway_url}/system/api/service/unregister/yet_another_service', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/service/test_service/api/health', headers=headers)
    assert response.status_code == 200, response.text

    headers = get_headers({
        'username': 'testuser',
        'password': 'secret',
    })

    response = http_client.get(f'{gateway_url}/system/api/service', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.post(f'{gateway_url}/system/api/service/register', headers=headers, json=data)
    assert response.status_code == 401, response.text

    response = http_client.delete(f'{gateway_url}/system/api/service/unregister/yet_another_service', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/service/test_service/api/health', headers=headers)
    assert response.status_code == 200, response.text

    headers = get_headers({
        'username': 'noman',
        'password': 'secret',
    })

    response = http_client.get(f'{gateway_url}/system/api/service', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.post(f'{gateway_url}/system/api/service/register', headers=headers, json=data)
    assert response.status_code == 401, response.text

    response = http_client.delete(f'{gateway_url}/system/api/service/unregister/yet_another_service', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/service/test_service/api/health', headers=headers)
    assert response.status_code == 200, response.text


def test_storage(http_client):
    minio_helpers.delete_all_buckets()

    headers = get_headers({
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    })

    bucket_name = 'mahbucket'
    bucket = {
        'bucket_name': bucket_name
    }

    file_name = 'test.txt'
    files = {
        'file': io.BytesIO(b'file data goes here')
    }

    response = http_client.post(f'{gateway_url}/system/api/storage/buckets', json=bucket, headers=headers)
    assert response.status_code == 201, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/buckets', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.post(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', files=files, headers=headers)
    assert response.status_code == 201, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', headers=headers)
    assert response.status_code == 200, response.text

    minio_helpers.delete_all_buckets()

    headers = get_headers({
        'username': 'root',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/system/api/storage/buckets', json=bucket, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/buckets', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.post(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', files=files, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', headers=headers)
    assert response.status_code == 401, response.text

    minio_helpers.delete_all_buckets()

    headers = get_headers({
        'username': 'testuser',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/system/api/storage/buckets', json=bucket, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/buckets', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.post(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', files=files, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', headers=headers)
    assert response.status_code == 401, response.text

    minio_helpers.delete_all_buckets()

    headers = get_headers({
        'username': 'noman',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/system/api/storage/buckets', json=bucket, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/buckets', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.post(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', files=files, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/storage/{bucket_name}/{file_name}', headers=headers)
    assert response.status_code == 401, response.text

    minio_helpers.delete_all_buckets()


def test_audit(clean_db, http_client):
    headers = get_headers({
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    })

    # create object
    data = {
        'content': 'testing testing'
    }

    response = http_client.post(f'{gateway_url}/infoflow/api/comment', json=data, headers=headers)
    assert response.status_code == 201, response.text
    _key = response.json().get('_key')

    audits = []
    for i in range(10):
        audits.append({
            'pre': {},
            'post': {
                '_id': f'comment/{_key}',
                'content': 'testing',
            },
        })

    response = http_client.post(f'{gateway_url}/system/api/audit_log', json=audits, headers=headers)
    assert response.status_code == 201, response.text

    response = http_client.get(f'{gateway_url}/system/api/audit_log/comment/{_key}', headers=headers)
    assert response.status_code == 200, response.text

    headers = get_headers({
        'username': 'root',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/system/api/audit_log', json=audits, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/audit_log/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'testuser',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/system/api/audit_log', json=audits, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/audit_log/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'noman',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/system/api/audit_log', json=audits, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/audit_log/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text


def test_domain_data_rest(http_client):
    headers = get_headers({
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    })

    data = {
        'content': 'testing testing'
    }

    partial = {
        'content': 'testing more'
    }

    response = http_client.post(f'{gateway_url}/infoflow/api/comment', json=data, headers=headers)
    assert response.status_code == 201, response.text
    _key = response.json().get('_key')

    response = http_client.get(f'{gateway_url}/infoflow/api/comment', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_neighbors', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_changes', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.patch(f'{gateway_url}/infoflow/api/comment/{_key}', json=partial, headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.delete(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'root',
        'password': 'secret',
    })


    response = http_client.post(f'{gateway_url}/infoflow/api/comment', json=data, headers=headers)
    assert response.status_code == 201, response.text
    _key = response.json().get('_key')

    response = http_client.get(f'{gateway_url}/infoflow/api/comment', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_neighbors', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_changes', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.patch(f'{gateway_url}/infoflow/api/comment/{_key}', json=partial, headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.delete(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'testuser',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/infoflow/api/comment', json=data, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_neighbors', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_changes', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.patch(f'{gateway_url}/infoflow/api/comment/{_key}', json=partial, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.delete(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'noman',
        'password': 'secret',
    })

    response = http_client.post(f'{gateway_url}/infoflow/api/comment', json=data, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_neighbors', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/comment/{_key}/_changes', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.patch(f'{gateway_url}/infoflow/api/comment/{_key}', json=partial, headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.delete(f'{gateway_url}/infoflow/api/comment/{_key}', headers=headers)
    assert response.status_code == 401, response.text


def test_domain_data_graphql(http_client):
    headers = get_headers({
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    })

    create_comment_query = '''
    mutation {
        createComment(input: { content: "test test" }) {
            _key
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': create_comment_query}, headers=headers)
    assert response.status_code == 200, response.text

    data = response.json()
    _key = data['data']['createComment'].pop('_key')

    get_comments_query = '''
    {
        CommentList {
            results {
                _key
            }
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comments_query}, headers=headers)
    assert response.status_code == 200, response.text

    get_comment_query = f'''
    {{
        Comment(_key: {_key}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comment_query}, headers=headers)
    assert response.status_code == 200, response.text

    update_comment_query = f'''
    mutation {{
        updateComment(_key: {_key}, input: {{ content: "test again" }}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': update_comment_query}, headers=headers)
    assert response.status_code == 200, response.text

    delete_comment_query = f'''
    mutation {{
        deleteComment(_key: {_key})
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': delete_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'root',
        'password': 'secret',
    })

    create_comment_query = '''
    mutation {
        createComment(input: { content: "test test" }) {
            _key
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': create_comment_query}, headers=headers)
    assert response.status_code == 200, response.text

    data = response.json()
    _key = data['data']['createComment'].pop('_key')

    get_comments_query = '''
    {
        CommentList {
            results {
                _key
            }
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comments_query}, headers=headers)
    assert response.status_code == 200, response.text

    get_comment_query = f'''
    {{
        Comment(_key: {_key}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comment_query}, headers=headers)
    assert response.status_code == 200, response.text

    update_comment_query = f'''
    mutation {{
        updateComment(_key: {_key}, input: {{ content: "test again" }}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': update_comment_query}, headers=headers)
    assert response.status_code == 200, response.text

    delete_comment_query = f'''
    mutation {{
        deleteComment(_key: {_key})
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': delete_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'testuser',
        'password': 'secret',
    })

    create_comment_query = '''
    mutation {
        createComment(input: { content: "test test" }) {
            _key
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': create_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    get_comments_query = '''
    {
        CommentList {
            results {
                _key
            }
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comments_query}, headers=headers)
    assert response.status_code == 200, response.text

    get_comment_query = f'''
    {{
        Comment(_key: {_key}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comment_query}, headers=headers)
    assert response.status_code == 200, response.text

    update_comment_query = f'''
    mutation {{
        updateComment(_key: {_key}, input: {{ content: "test again" }}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': update_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    delete_comment_query = f'''
    mutation {{
        deleteComment(_key: {_key})
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': delete_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    headers = get_headers({
        'username': 'noman',
        'password': 'secret',
    })

    create_comment_query = '''
    mutation {
        createComment(input: { content: "test test" }) {
            _key
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': create_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    get_comments_query = '''
    {
        CommentList {
            results {
                _key
            }
        }
    }
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comments_query}, headers=headers)
    assert response.status_code == 401, response.text

    get_comment_query = f'''
    {{
        Comment(_key: {_key}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': get_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    update_comment_query = f'''
    mutation {{
        updateComment(_key: {_key}, input: {{ content: "test again" }}) {{
            _key
        }}
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': update_comment_query}, headers=headers)
    assert response.status_code == 401, response.text

    delete_comment_query = f'''
    mutation {{
        deleteComment(_key: {_key})
    }}
    '''

    response = http_client.post(f'{gateway_url}/infoflow/graphql', json={'query': delete_comment_query}, headers=headers)
    assert response.status_code == 401, response.text
