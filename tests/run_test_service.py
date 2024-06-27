import asyncio
import os
import logging
import httpx

from sanic import Sanic
from sanic.response import json, empty


def trueish(value):
    return value in (True, 'True', 'true', 'yes', 'on', '1', 1)


logger = logging.getLogger()

app = Sanic('test_service')

GATEWAY_URL = 'https://memoriam-gateway:5001'
DEBUG = trueish(os.getenv('DEBUG', False))
CERT_FILE = os.getenv('CERT_FILE')
KEY_FILE = os.getenv('KEY_FILE')
CA_FILE = os.getenv('CA_FILE', True) or False
TLS_CONFIG = {
    'cert': CERT_FILE,
    'key': KEY_FILE,
    # TODO: these are hacks for 22.9,
    # report or replace by path or SSLContext
    'creator': 'mkcert',
    'localhost': 'localhost',
} if (CERT_FILE and KEY_FILE) else None


def get_auth_headers():
    data = {
        'serviceName': 'testservice',
        'serviceSecret': 'secret',
    }
    response = httpx.post(f'{GATEWAY_URL}/authly/api/auth/authenticate', json=data, verify=False)
    assert response.status_code == 200, response.text
    token = response.json().get('token')

    return {
        'Authorization': f'Bearer {token}'
    }


@app.get('/api/health')
async def health(request):
    return json('Ok')


@app.get('/api/failing_endpoint')
async def failing_endpoint(request):
    return None


@app.post('/api/pre_access_obj_search_result')
async def pre_access_obj_search_result(request):
    objs = request.json

    for obj in objs:
        obj['ping'] = 'pong'

        # _key = obj.get('_key')
        # if _key:
        #     headers = get_auth_headers()
        #     async with httpx.AsyncClient(http2=True, verify=False) as client:
        #         response = await client.get(
        #             f'{GATEWAY_URL}/infoflow/api/search_result/{_key}/comments',
        #             headers=headers
        #         )
        #     assert response.status_code == 200, response.text
        #     obj['comments'] = response.json().get('results')

    return json(objs)


@app.post('/api/pre_create_obj_search_result')
async def pre_create_obj_search_result(request):
    obj = request.json
    obj['touched'] = 'for the very first time'
    return json(obj)


@app.post('/api/pre_update_obj_search_result')
async def pre_update_obj_search_result(request):
    obj = request.json
    obj['touched'] = 'by all this attention'
    return json(obj)


@app.post('/api/pre_access_rel_search_result_comments')
async def pre_access_rel_search_result_comments(request):
    objs = request.json

    for obj in objs:
        obj['content'] += '!!!'

    return json(objs)


@app.post('/api/pre_create_rel_search_result_comments')
async def pre_create_rel_search_result_comments(request):
    obj = request.json
    obj['content'] += '!'
    return json(obj)


@app.post('/api/pre_update_rel_search_result_comments')
async def pre_update_rel_search_result_comments(request):
    obj = request.json
    obj['content'] += '!'
    return json(obj)


@app.post('/api/post_create_obj_search_result')
async def post_create_obj_search_result(request):
    obj = request.json
    return empty()


@app.post('/api/post_update_obj_search_result')
async def post_update_obj_search_result(request):
    obj = request.json
    return empty()


@app.post('/api/post_delete_obj_search_result')
async def post_delete_obj_search_result(request):
    obj = request.json
    return empty()


@app.post('/api/pre_create_obj_notification_rule')
async def pre_create_obj_notification_rule(request):
    return None


@app.post('/api/pre_create_obj_meta')
async def pre_create_obj_meta(request):
    obj = request.json
    assert '_meta' in obj

    data = {
        'collections': {
            'write': 'comment'
        }
    }
    headers = get_auth_headers()
    response = httpx.post(
        f'{GATEWAY_URL}/_db/memoriam_test/_api/transaction/begin',
        json=data,
        headers=headers,
        verify=False
    )
    assert response.status_code == 201, response.text

    headers = {
        'x-arango-trx-id': response.json()['result']['id']
    }
    return json(obj, headers=headers)


@app.post('/api/post_create_obj_meta')
async def post_create_obj_meta(request):
    obj = request.json
    assert '_meta' in obj['post']

    trx_id = request.headers.get('x-arango-trx-id')
    assert trx_id is not None

    headers = get_auth_headers()
    response = httpx.put(
        f'{GATEWAY_URL}/_db/memoriam_test/_api/transaction/{trx_id}',
        headers=headers,
        verify=False
    )
    assert response.status_code == 200, response.text

    return empty()


@app.post('/api/transaction_with_audit')
async def transaction_with_audit(request):
    # start transaction
    trx_data = {
        'collections': {
            'write': ['data', 'audit_log']
        }
    }
    headers = get_auth_headers()
    response = httpx.post(
        f'{GATEWAY_URL}/_db/memoriam_test/_api/transaction/begin',
        json=trx_data,
        headers=headers,
        verify=False
    )
    assert response.status_code == 201, response.text
    trx_id = response.json()['result']['id']

    headers['x-arango-trx-id'] = trx_id
    try:
        # create document manually
        query = {
            'query': 'INSERT @document INTO data RETURN NEW',
            'bindVars': {
                'document': request.json
            }
        }
        response = httpx.post(
            f'{GATEWAY_URL}/_db/memoriam_test/_api/cursor',
            json=query,
            headers=headers,
            verify=False
        )
        assert response.status_code == 201, response.text
        data = response.json().get('result', [{}])[0]
        _key = data.get('_key')

        # create audit manually
        audit_data = [
            {
                'pre': {},
                'post': data,
            },
            # test empty audit
            {
                'pre': {},
                'post': {}
            }
        ]
        response = httpx.post(
            f'{GATEWAY_URL}/system/api/audit_log',
            json=audit_data,
            headers=headers,
            verify=False
        )
        assert response.status_code == 201, response.text
        assert len(response.json()) == 1

        # commit transaction
        del headers['x-arango-trx-id']
        response = httpx.put(
            f'{GATEWAY_URL}/_db/memoriam_test/_api/transaction/{trx_id}',
            headers=headers,
            verify=False
        )
        assert response.status_code == 200, response.text

    except AssertionError as e:
        logger.error(e)

        # abort transaction
        del headers['x-arango-trx-id']
        response = httpx.delete(
            f'{GATEWAY_URL}/_db/memoriam_test/_api/transaction/{trx_id}',
            headers=headers,
            verify=False
        )
        assert response.status_code == 200, response.text
        return empty(500)

    return empty(200)


@app.websocket('/api/ws_echo')
async def websocket_echo(request, ws):
    async for msg in ws:
        await ws.send(msg)


@app.websocket('/api/ws_beacon')
async def websocket_beacon(request, ws):
    while True:
        await ws.send('Ping!')
        await asyncio.sleep(1)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=DEBUG, ssl=TLS_CONFIG)
