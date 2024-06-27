import asyncio
import time
import logging

import httpx
from httpx_ws import aconnect_ws, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from wsproto.events import TextMessage, BytesMessage

from sanic import Websocket
from sanic.exceptions import SanicException
from sanic.response import raw

from memoriam.config import CA_FILE, REQUEST_TIMEOUT, WEBSOCKET_LOOP_TIMEOUT, WEBSOCKET_PING_INTERVAL, WEBSOCKET_PING_TIMEOUT
from memoriam.utils import scrub_headers


logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')


def get_reverse_proxy(base_url, name):
    """Get a reverse proxy handler for the given base path"""

    async def reverse_proxy(request, path=None):
        """Reverse proxy handler for requests routed through gateway"""
        url = f'{base_url}'
        if path:
            url += f'/{path}'
        if request.query_string:
            url += f'?{request.query_string}'

        pre_proxy = time.perf_counter() * 1000

        async with httpx.AsyncClient(verify=CA_FILE, timeout=REQUEST_TIMEOUT) as client:
            try:
                proxy_response = await client.request(
                    method=request.method,
                    url=url,
                    content=request.body,
                    headers=scrub_headers(request.headers),
                    cookies=dict(request.cookies)
                )
            except httpx.RequestError as e:
                raise SanicException(f'Error while requesting {e.request.url}: {e}') from None

        log_perf.debug(f'{name} reverse proxy response time: {(time.perf_counter() * 1000 - pre_proxy):.2f} ms')

        return raw(
            body=proxy_response.content,
            status=proxy_response.status_code,
            headers=dict(scrub_headers(proxy_response.headers))
        )

    return reverse_proxy


async def ws_connection(
        downstream: Websocket,
        upstream_url: str,
        upstream_ping: bool = False
    ):
    """Unified bidirectional websocket connection handler"""
    async with httpx.AsyncClient(verify=CA_FILE) as client:
        async with aconnect_ws(upstream_url, client,
                keepalive_ping_interval_seconds=(WEBSOCKET_PING_INTERVAL if upstream_ping else None),
                keepalive_ping_timeout_seconds=(WEBSOCKET_PING_TIMEOUT if upstream_ping else None),
            ) as upstream:
            while True:
                try:
                    # downstream, or inbound from client
                    msg = await downstream.recv(WEBSOCKET_LOOP_TIMEOUT)
                    if isinstance(msg, str):
                        await upstream.send_text(msg)
                    elif isinstance(msg, bytes):
                        await upstream.send_bytes(msg)

                    # upstream, or outbound from server
                    event = await upstream.receive(WEBSOCKET_LOOP_TIMEOUT)
                    if (isinstance(event, TextMessage) or
                        isinstance(event, BytesMessage)):
                        await downstream.send(event.data)

                except asyncio.TimeoutError:
                    pass

                except ConnectionClosed:
                    await upstream.close()
                    break

                except WebSocketDisconnect:
                    await downstream.close()
                    break


def get_ws_reverse_proxy(base_url):
    """Get a reverse proxy handler for websockets"""

    async def ws_reverse_proxy(request, ws, path=None):
        """Reverse proxy handler for websockets"""
        url = f'{base_url}'
        if path:
            url += f'/system/api/ws/{path}'

        entity_id = request.headers.get('x-authly-entity-id')
        url += f'?x-authly-entity-id={entity_id}'
        if request.query_string:
            url += f'&{request.query_string}'

        await ws_connection(ws, url)


    return ws_reverse_proxy
