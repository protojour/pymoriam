import pathlib

import pytest
import httpx

import tests.helpers.minio as minio_helpers
import tests.helpers.utils as utils
from tests.conftest import gateway_url, storage_url


DATA_PATH = pathlib.Path(__file__, '..', 'data').resolve()


@pytest.fixture(autouse=True, scope='module')
def setup_teardown_module(wait_for_system_api):
    minio_helpers.delete_all_buckets()
    yield
    minio_helpers.delete_all_buckets()


@pytest.fixture(autouse=True, scope='module')
def headers():
    payload = {
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    }

    response = httpx.post(f'{gateway_url}/authly/api/auth/authenticate', json=payload, verify=False)
    assert response.status_code == 200, response.text

    token = response.json().get('token')
    return {
        'Authorization': f'Bearer {token}'
    }


def test_post_bucket(wait_for_system_api, http_client, headers):
    response = http_client.post(f'{storage_url}/system/api/storage/buckets', json={'bucket_name': 'gg'}, timeout=10, headers=headers)
    assert response.status_code == 400, response.text  # should fail, invalid bucket name

    response = http_client.post(f'{storage_url}/system/api/storage/buckets', json={'bucket_name': 'testbucket0'}, timeout=10, headers=headers)
    assert response.status_code == 201, response.text

    response = http_client.post(f'{storage_url}/system/api/storage/buckets', json={'bucket_name': 'testbucket0'}, timeout=10, headers=headers)
    assert response.status_code == 409, response.text  # should fail, bucket exists

    response = http_client.post(f'{storage_url}/system/api/storage/buckets', json={'bucket_name': 'testbucket1'}, timeout=10, headers=headers)
    assert response.status_code == 201, response.text

    response = http_client.post(f'{storage_url}/system/api/storage/buckets', json={'bucket_name': 'testbucket2'}, timeout=10, headers=headers)
    assert response.status_code == 201, response.text


def test_list_buckets(wait_for_storage_api, http_client, headers):
    response = http_client.get(f'{storage_url}/system/api/storage/buckets', timeout=10, headers=headers)
    assert response.json()[0]['bucket_name'] == 'testbucket0'
    assert response.json()[1]['bucket_name'] == 'testbucket1'
    assert response.json()[2]['bucket_name'] == 'testbucket2'


def test_add_object(wait_for_system_api, http_client, headers):
    response = http_client.post(f'{storage_url}/system/api/storage/testbucket2/testobject.txt', timeout=20, headers=headers)
    assert response.status_code == 400, response.text  # should fail, body is required

    files = {'file': open(f'{DATA_PATH}/testobject.txt', 'rb')}
    response = http_client.post(f'{storage_url}/system/api/storage/nonexistingbucket/testobject.txt', files=files, timeout=20, headers=headers)
    assert response.status_code == 404, response.text  # should fail, bucket does not exist

    files = {'file': open(f'{DATA_PATH}/testobject.txt', 'rb')}
    response = http_client.post(f'{storage_url}/system/api/storage/testbucket2/testobject.txt', files=files, timeout=20, headers=headers)
    assert response.status_code == 201, response.text

    files = {'file': open(f'{DATA_PATH}/testobject.txt', 'rb')}
    response = http_client.post(f'{storage_url}/system/api/storage/testbucket2/testobject.txt', files=files, timeout=20, headers=headers)
    assert response.status_code == 409, response.text  # should fail, object already exists


def test_get_object(wait_for_system_api, http_client, headers):
    response = http_client.get(f'{storage_url}/system/api/storage/testbucket2/nonexistingobject.txt', timeout=10, headers=headers)
    assert response.status_code == 404, response.text  # should fail, object does not exist

    response = http_client.get(f'{storage_url}/system/api/storage/nonexistingbucket/testobject.txt', timeout=10, headers=headers)
    assert response.status_code == 404, response.text  # should fail, bucket does not exist

    filedata = open(f'{DATA_PATH}/testobject.txt', 'rb').read()
    response = http_client.get(f'{storage_url}/system/api/storage/testbucket2/testobject.txt', timeout=10, headers=headers)
    assert response.status_code == 200, response.text
    assert response.content == filedata


def test_get_bucket(wait_for_system_api, http_client, headers):
    response = http_client.get(f'{storage_url}/system/api/storage/nonexistingbucket', timeout=10, headers=headers)
    assert response.status_code == 404, response.text  # should fail, bucket does not exist

    response = http_client.get(f'{storage_url}/system/api/storage/testbucket2', timeout=10, headers=headers)
    assert response.status_code == 200, response.text


large_size = utils._1000MB - utils._1MB


def test_post_large_stream(wait_for_system_api, http_client, headers):
    response = http_client.post(
        f'{storage_url}/system/api/storage/testbucket0/testlargeobjectstream',
         data=utils.random_data_gen(large_size, utils._5MB),  # type: ignore
         headers={
            **headers,
            'Content-type':'application/octet-stream',
            'Content-disposition':'attachment; filename="testname"'
        },
        timeout=12
    )
    assert response.status_code == 201, response.text


def test_get_large_stream(wait_for_system_api, http_client, headers):
    stream_size = 0
    with http_client.stream('GET', f'{storage_url}/system/api/storage/testbucket0/testlargeobjectstream', timeout=12, headers=headers) as response:
        response.read()
        assert response.status_code == 200, response.text

        for chunk in response.iter_bytes():
            stream_size += len(chunk)

    assert stream_size == large_size
