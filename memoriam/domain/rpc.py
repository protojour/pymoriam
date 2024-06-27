import asyncio
import logging
import time
from typing import Tuple

import httpx
import ujson as json
from sanic.exceptions import SanicException

from memoriam.config import CA_FILE, REQUEST_TIMEOUT
from memoriam.utils import scrub_headers


logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')


async def get_listeners(channel, request):
    """Get registered RPC listeners for the given channel from the Service RPC cache"""
    cache = request.app.ctx.cache
    service_rpcs = await cache.get('service_rpcs', {})
    listeners = service_rpcs.get(channel, [])
    return listeners


async def _call_listeners(channel, listeners, obj, request):
    """Fetch and call registered RPC listeners sequentially for the given channel"""
    start = time.perf_counter() * 1000
    headers = scrub_headers(dict(request.headers))
    trx_id = headers.get('x-arango-trx-id', '')

    async with httpx.AsyncClient(http2=True, verify=CA_FILE, timeout=REQUEST_TIMEOUT) as client:
        for listener in listeners:
            try:
                response = await client.post(listener, json=obj, headers=headers)
                if response.status_code in (200, 204):
                    if channel[:3] == 'pre':
                        try:
                            obj = response.json()
                            trx_id = response.headers.get('x-arango-trx-id', trx_id)
                            headers['x-arango-trx-id'] = trx_id
                        except json.JSONDecodeError as e:
                            raise SanicException(str(e), status_code=500) from None
                else:
                    raise SanicException(response.text, status_code=response.status_code) from None
            except httpx.RequestError as e:
                raise SanicException(f'Error while requesting {e.request.url}: {e}') from None

    log_perf.debug(f'Call {channel} RPC listeners time: {(time.perf_counter() * 1000 - start):.2f} ms')

    return obj, trx_id


async def pre_rpc(channel, listeners, obj, request) -> Tuple:
    """Call all registered pre object RPC listeners"""
    return await _call_listeners(channel, listeners, obj, request)


async def post_rpc(channel, listeners, pre, post, request):
    """Call all registered post object RPC listeners. Will yield to calling coroutine before continuing."""
    await asyncio.sleep(0)
    obj = {
        'pre': pre,
        'post': post,
    }
    await _call_listeners(channel, listeners, obj, request)
