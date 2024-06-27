import httpx

from tests.conftest import gateway_url


def test_healthcheck(wait_for_system_api, wait_for_storage_api):
    response = httpx.get(f'{gateway_url}/health', verify=False)
    assert response.status_code == 200, response.json()
