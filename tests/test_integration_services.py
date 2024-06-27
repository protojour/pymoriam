from httpx_ws import connect_ws

from tests.conftest import domain_url


def test_register_service(wait_for_system_api, http_client):
    data = {
        'name': 'Another Service',
        'info': 'This is another service',
        'host': 'https://another-service:6001',
        'api': '/api'
    }
    response = http_client.post(f'{domain_url}/system/api/service/register', json=data)
    assert response.status_code == 201, response.json()


def test_service_status(wait_for_system_api, http_client):
    response = http_client.get(f'{domain_url}/system/api/service')
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data
    assert data.get('test_service', {}).get('info') == 'This is a test service'
    assert data.get('test_client', {}).get('info') == 'This is a test client'
    assert data.get('another_service', {}).get('info') == 'This is another service'


def test_unregister_service(wait_for_system_api, http_client):
    response = http_client.delete(f'{domain_url}/system/api/service/unregister/another_service')
    assert response.status_code == 204, response.json()


def test_service_api_proxy(wait_for_system_api, http_client):
    response = http_client.get(f'{domain_url}/system/api/service/test_service/api/health')
    assert response.status_code == 200, response.json()
    assert response.json() == 'Ok'


def test_service_rpc_endpoints(wait_for_system_api, http_client):
    objs = [{
        'test': 'test'
    }]

    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/pre_access_obj_search_result', json=objs)
    assert response.status_code == 200, response.json()
    assert response.json() == [{
        'test': 'test',
        'ping': 'pong'
    }]

    obj = objs[0]
    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/pre_create_obj_search_result', json=obj)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'test': 'test',
        'touched': 'for the very first time'
    }

    obj = response.json()
    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/pre_update_obj_search_result', json=obj)
    assert response.status_code == 200, response.json()
    assert response.json() == {
        'test': 'test',
        'touched': 'by all this attention'
    }

    obj = response.json()
    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/pre_delete_obj_search_result', json=obj)
    assert response.status_code == 404, response.json()

    obj = {'pre': {'test': 'test'}, 'post': {'test': 'toast'}}

    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/post_create_obj_search_result', json=obj)
    assert response.status_code == 204

    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/post_update_obj_search_result', json=obj)
    assert response.status_code == 204

    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/post_delete_obj_search_result', json=obj)
    assert response.status_code == 204


def test_service_rpc_flow_with_meta(wait_for_system_api, clean_db, http_client):
    obj = {
        '_meta': {
            'meta': 'test'
        },
        'name': 'test',
        'description': 'description',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/search_result', json=obj)
    assert response.status_code == 201, response.json()

    obj = response.json()
    _key = obj['_key']
    assert obj['name'] == 'test'
    assert obj['description'] == 'description'
    assert obj['touched'] == 'for the very first time'
    assert '_meta' not in obj

    response = http_client.get(f'{domain_url}/infoflow/api/search_result/{_key}')
    assert response.status_code == 200, response.json()

    obj = response.json()
    assert obj['name'] == 'test'
    assert obj['description'] == 'description'
    assert obj['ping'] == 'pong'
    assert obj['touched'] == 'for the very first time'
    assert '_meta' not in obj

    obj = {
        '_meta': {
            'meta': 'test again'
        },
        'description': 'updated description'
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/search_result/{_key}', json=obj)
    assert response.status_code == 200, response.json()

    obj = response.json()
    assert obj['name'] == 'test'
    assert obj['description'] == 'updated description'
    assert obj['touched'] == 'by all this attention'
    assert '_meta' not in obj


def test_service_bulk_rpc_flow_with_meta(wait_for_system_api, clean_db, http_client):
    objs = [
        {
            '_meta': {
                'meta': 'bulk test 1'
            },
            'name': 'bulk test 1',
            'description': 'description 1',
        },
        {
            '_meta': {
                'meta': 'bulk test 2'
            },
            'name': 'bulk test 2',
            'description': 'description 2',
        }
    ]

    response = http_client.post(f'{domain_url}/infoflow/api/search_result/_bulk', json=objs)
    assert response.status_code == 201, response.json()

    for result in response.json():
        assert '_meta' not in result['new']

    params = {
        'filter': [
            'name LIKE "bulk test%"'
        ]
    }
    response = http_client.get(f'{domain_url}/infoflow/api/search_result')
    assert response.status_code == 200, response.json()

    objs = []
    for result in response.json().get('results'):
        assert '_meta' not in result

        obj = {}
        obj['_meta'] = {
            'meta': result['name']
        }
        obj['_key'] = result['_key']
        obj['name'] = result['name']
        obj['description'] = result['description'] + ' 2 too'

        objs.append(obj)

    response = http_client.patch(f'{domain_url}/infoflow/api/search_result/_bulk', json=objs)
    assert response.status_code == 200, response.json()

    for result in response.json():
        assert '_meta' not in result['new']


def xtest_service_relation_rpc_flow(wait_for_system_api, clean_db, http_client):
    obj = {
        'name': 'test 2',
        'description': 'description',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/search_result', json=obj)
    assert response.status_code == 201, response.json()

    obj = response.json()
    _key = obj['_key']

    obj = {
        'content': 'this is a test'
    }
    response = http_client.post(f'{domain_url}/infoflow/api/search_result/{_key}/comments', json=obj)
    assert response.status_code == 200, response.json()

    obj = response.json()
    assert obj['content'] == 'this is a test!'

    obj = {
        'content': 'this is still a test'
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/search_result/{_key}/comments', json=obj)
    assert response.status_code == 200, response.json()

    obj = response.json()
    assert obj['content'] == 'this is still a test!'


def test_failing_service(wait_for_system_api, http_client):
    response = http_client.get(f'{domain_url}/system/api/service/test_service/api/failing_endpoint')
    assert response.status_code == 500, response.text


def test_failing_rpc_flow(wait_for_system_api, clean_db, http_client):
    obj = {
        'name': 'test',
        'rules': 'rules',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/notification_rule', json=obj)
    assert response.status_code == 500, response.text


def test_meta_transaction(wait_for_system_api, clean_db, http_client):
    obj = {
        'data': 'data'
    }

    response = http_client.post(f'{domain_url}/infoflow/api/meta', json=obj)
    assert response.status_code == 201, response.text


def test_transaction_with_audit(wait_for_system_api, clean_db, http_client):
    data = {
        'data': 'data',
    }

    response = http_client.post(f'{domain_url}/system/api/service/test_service/api/transaction_with_audit', json=data)
    assert response.status_code == 200, response.text


def test_websocket_reverse_proxy(wait_for_system_api):
    with connect_ws(f'{domain_url}/system/api/ws/service/test_service/api/ws_echo') as ws:
        ws.send_text('ECHO!')
        message = ws.receive_text(timeout=1)
        assert message == 'ECHO!'

        pong = ws.ping()
        assert pong.wait(timeout=1)

        ws.send_text('ECHO!')
        message = ws.receive_text(timeout=1)
        assert message == 'ECHO!'


def test_websocket_proxied_beacon(wait_for_system_api):
    with connect_ws(f'{domain_url}/system/api/ws/service/test_service/api/ws_beacon') as ws:
        message = ws.receive_text(timeout=2)
        assert message == 'Ping!'

        message = ws.receive_text(timeout=2)
        assert message == 'Ping!'
