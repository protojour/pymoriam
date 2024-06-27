
from tests.conftest import domain_url


def test_list_domains(clean_db, http_client):
    response = http_client.get(f'{domain_url}/system/api/domain')
    assert response.status_code == 200, response.json()
    assert len(response.json()) == 1


def test_validate_domain(clean_db, http_client):
    bad_domain = {
        'label': 'Test Domain',
        'description': 'A domain without schema',
    }

    response = http_client.post(f'{domain_url}/system/api/domain/validate', json=bad_domain)
    assert response.status_code == 400, response.json()

    good_domain = {
        'label': 'Test Domain',
        'description': 'A domain including schema',
        'schema': '''
            a:
                description: Test object a
                resolver: entity
                attributes: {}
                relations: {}

            b:
                description: Test object b
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }

    response = http_client.post(f'{domain_url}/system/api/domain/validate', json=good_domain)
    assert response.status_code == 200, response.json()


def test_post_domain(clean_db, http_client):
    good_domain = {
        'label': 'Test Domain',
        'description': 'A domain including schema',
        'schema': '''
            a:
                description: Test object a
                resolver: entity
                attributes: {}
                relations: {}

            b:
                description: Test object b
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }

    response = http_client.post(f'{domain_url}/system/api/domain', json=good_domain)
    assert response.status_code == 201, response.json()
    assert response.json()

    bad_domain = {
        'label': 'test domain',
        'description': 'A domain with a similar name',
        'schema': ''
    }

    response = http_client.post(f'{domain_url}/system/api/domain', json=bad_domain)
    assert response.status_code == 409, response.json()


def test_get_domain(clean_db, http_client):
    response = http_client.get(f'{domain_url}/system/api/domain')
    assert response.status_code == 200, response.json()
    assert len(response.json()) == 2

    domain_key = 'test_domain'
    response = http_client.get(f'{domain_url}/system/api/domain/{domain_key}')
    assert response.status_code == 200, response.json()
    assert response.json()['_key'] == domain_key


def test_patch_domain(clean_db, http_client):
    domain_key = 'test_domain'
    partial = {
        'label': 'Changed Test Domain'
    }
    response = http_client.patch(f'{domain_url}/system/api/domain/{domain_key}', json=partial)
    assert response.status_code == 200, response.json()
    assert response.json()['label'] == partial['label']

    another_domain = {
        'label': 'Another Test Domain',
        'description': 'Another domain',
        'schema': '''
            c:
                description: Test object c
                resolver: entity
                attributes: {}
                relations: {}
        '''
    }

    response = http_client.post(f'{domain_url}/system/api/domain', json=another_domain)
    assert response.status_code == 201, response.json()

    partial = {
        'label': 'another test domain'
    }
    response = http_client.patch(f'{domain_url}/system/api/domain/{domain_key}', json=partial)
    assert response.status_code == 409, response.json()


def test_delete_domain(clean_db, http_client):
    domain_key = 'test_domain'

    response = http_client.delete(f'{domain_url}/system/api/domain/{domain_key}')
    assert response.status_code == 204, response.json()

    response = http_client.get(f'{domain_url}/system/api/domain/{domain_key}')
    assert response.status_code == 404, response.json()

    domain_key = 'another_test_domain'

    response = http_client.delete(f'{domain_url}/system/api/domain/{domain_key}')
    assert response.status_code == 204, response.json()

    response = http_client.get(f'{domain_url}/system/api/domain/{domain_key}')
    assert response.status_code == 404, response.json()
