import asyncio
import logging
from functools import partial

import httpx
import ujson as json

from memoriam.config import (
    AUTHLY_SERVICENAME, AUDIT_LOG, AUDIT_LOG_DB, AUDIT_VERSIONING,
    ARANGO_CONNECT_RETRIES, ARANGO_CONNECT_BACKOFF, ARANGO_DB_NAME,
    STORAGE_SCHEME, STORAGE_HOST, STORAGE_PORT, CA_FILE
)
from memoriam.arangodb import get_arangodb, get_diffs, prettify_aql
from memoriam.utils import iso8601_now, get_user_id, task_handler


logger = logging.getLogger('memoriam')
log_audit = logging.getLogger('memoriam.audit')
log_error = logging.getLogger('memoriam.error')


def set_creator(obj, request):
    """Set creator attribute to user id provided by auth service"""
    obj['creator'] = get_user_id(request)
    return obj


def set_created(obj):
    """Set created attribute to current ISO-8601 datetime"""
    obj['created'] = iso8601_now()
    return obj


def set_updated(obj):
    """Set updated attribute to current ISO-8601 datetime,
       use value from created on first run"""
    if 'updated' not in obj and 'created' in obj:
        obj['updated'] = obj['created']
    else:
        obj['updated'] = iso8601_now()
    return obj


async def audit(pre, post, request, edge=False, note=None):
    """Generate audit log entries and write to log, database"""
    await asyncio.sleep(0)

    db = await get_arangodb()
    data = generate_audit(pre, post, request, edge, note)

    if AUDIT_LOG:
        log_audit.info(f'Audit: {data}')

    if AUDIT_LOG_DB:
        query = prettify_aql(f'''
        INSERT {json.dumps(data)}
        IN audit_log
        RETURN NEW
        ''')
        result = db.aql(query)
        result = result['result'][0] if result['result'] else {}

        if post and AUDIT_VERSIONING:
            trx_id = request.headers.get('x-arango-trx-id')
            if trx_id:
                # defer version update until transaction is done
                coro = partial(defer_update_version, result, trx_id)
                task = request.app.add_task(coro)
                task.add_done_callback(task_handler)
            else:
                # no transaction, update version
                await update_version(result)

        return result

    return data


def generate_audit(pre, post, request, edge, note):
    """Generate structure for audit log"""
    pre_diff, post_diff = get_diffs(pre, post)

    if post and not pre:
        operation = 'create'
    elif pre and not post:
        operation = 'delete'
    else:
        operation = 'update'

    if not pre_diff and not post_diff:
        return

    return {
        'operation': operation,
        'parent': post.get('_version') or pre.get('_version'),
        'trx_id': request.headers.get('x-arango-trx-id'),
        'changed_id': post.get('_id') or pre.get('_id'),
        'from_id': post.get('_from') or pre.get('_from'),
        'to_id': post.get('_to') or pre.get('_to'),
        'edge': edge,
        'note': note,
        'created': post.get('updated') or post.get('created') or iso8601_now(),
        'creator': get_user_id(request),
        'pre': pre_diff,
        'post': post_diff,
    }


async def defer_update_version(audit_log, trx_id):
    """Audit task – wait for transaction to complete before running update_version"""
    for _ in range(ARANGO_CONNECT_RETRIES):

        url = f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}/_db/{ARANGO_DB_NAME}/_api/transaction/{trx_id}'
        headers = {
            'x-authly-entity-id': AUTHLY_SERVICENAME,
            'x-authly-entity-type': 'Service',
        }
        response = httpx.get(url, headers=headers, verify=CA_FILE)
        status = response.json().get('result', {}).get('status')

        if status == 'committed':
            await update_version(audit_log)
            break

        if status == 'aborted':
            break

        await asyncio.sleep(ARANGO_CONNECT_BACKOFF)

    else:
        obj_id = audit_log.get('changed_id')
        audit_id = audit_log.get('_id')
        log_error.error(f'Transaction {trx_id} did not complete while deferring update of _version of {obj_id} to "{audit_id}"')


async def update_version(audit_log):
    """Audit task – update version field with audit log _id"""
    db = await get_arangodb()
    collection, _key = audit_log['changed_id'].split('/')

    query = prettify_aql(f'''
    UPDATE "{_key}" WITH {{"_version": "{audit_log['_id']}"}}
    IN {collection}
    ''')
    db.aql(query)
