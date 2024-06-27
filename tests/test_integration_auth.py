
from tests.conftest import gateway_url


def test_unauthenticated(clean_db, http_client):
    # should pass
    response = http_client.get(f'{gateway_url}/onto')
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/onto/index.html')
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/system/api')
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/system/api/openapi.json')
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api')
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/api/openapi.json')
    assert response.status_code == 200, response.text

    # should not pass
    response = http_client.get(f'{gateway_url}/system/api/domain')
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/system/api/service')
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/infoflow/graphql')
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/_db/_system/_api/version')
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/_api/version')
    assert response.status_code == 401, response.text

    obj = {
        'name': 'test object',
        'description': '...for the first test'
    }
    response = http_client.post(f'{gateway_url}/infoflow/api/dataset', json=obj)
    assert response.status_code == 401, response.text


def test_authenticated(clean_db, http_client):
    payload = {
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    }

    # authenticate
    response = http_client.post(f'{gateway_url}/authly/api/auth/authenticate', json=payload)
    assert response.status_code == 200, response.text

    token = response.json().get('token')
    headers = {
        'Authorization': f'Bearer {token}'
    }

    # check session
    response = http_client.get(f'{gateway_url}/authly/api/auth/session', headers=headers)
    assert response.status_code == 200, response.text

    # denylist
    response = http_client.get(f'{gateway_url}/authly/api/docs', headers=headers)
    assert response.status_code == 401, response.text

    response = http_client.get(f'{gateway_url}/authly/api/docs/openapi.yaml', headers=headers)
    assert response.status_code == 401, response.text

    # should now pass
    response = http_client.get(f'{gateway_url}/system/api/domain', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/system/api/service', headers=headers)
    assert response.status_code == 200, response.text

    response = http_client.get(f'{gateway_url}/infoflow/graphql', headers=headers)
    assert response.status_code == 200, response.text

    # response = http_client.get(f'{gateway_url}/_admin/status', headers=headers, follow_redirects=True)
    # assert response.status_code == 200, response.text

    # test post, set_creator
    obj = {
        'name': 'another test object',
        'description': '...for the second test'
    }
    response = http_client.post(f'{gateway_url}/infoflow/api/dataset', headers=headers, json=obj)
    assert response.status_code == 201, response.text
    assert response.json().get('creator') == 'testservice', response.text

    # test authenticate, post, set_creator for user
    payload = {
        'username': 'testuser',
        'password': 'secret',
    }

    response = http_client.post(f'{gateway_url}/authly/api/auth/authenticate', json=payload)
    assert response.status_code == 200, response.text

    token = response.json().get('token')
    headers = {
        'Authorization': f'Bearer {token}'
    }

    obj = {
        'name': 'another test object still',
        'description': '...for the third test'
    }
    response = http_client.post(f'{gateway_url}/infoflow/api/dataset', headers=headers, json=obj)
    assert response.status_code == 201, response.text
    assert response.json().get('creator') == 'testuser', response.text

    # response = http_client.get(f'{gateway_url}/_admin/status', headers=headers, follow_redirects=True)
    # assert response.status_code == 401, response.text

