import time

from unittest.mock import MagicMock, AsyncMock

import pytest

from sanic.request import Request

import memoriam.domain.triggers
from memoriam.domain.triggers import *


def test_set_creator():
    obj = {}
    request = MagicMock(Request)
    request.headers = {'x-authly-entity-id': 'test'}

    obj = set_creator(obj, request)

    assert obj['creator'] == 'test'


def test_set_created():
    obj = {}
    obj = set_created(obj)

    assert len(obj['created']) == 27
    assert obj['created'][-1] == 'Z'
    assert obj['created'][:2] == '20'  # time travel safeguard


def test_set_updated():
    obj = {}
    obj = set_updated(obj)

    assert obj['updated']

    obj = {}
    obj = set_created(obj)
    obj = set_updated(obj)

    assert obj['updated'] == obj['created']

    time.sleep(0.01)
    obj = set_updated(obj)

    assert obj['updated'] != obj['created']


@pytest.mark.asyncio
async def test_audit():
    db = MagicMock()
    result = {
        'result': [{'_id': 'audit_log/1', 'changed_id': 'test/1'}]
    }
    db.aql = MagicMock(return_value=result)
    db.ping = MagicMock()

    memoriam.domain.triggers.get_arangodb = AsyncMock(return_value=db)

    memoriam.domain.triggers.AUDIT_LOG_DB = False
    memoriam.domain.triggers.AUDIT_VERSIONING= False
    request = MagicMock(Request)
    pre = {}
    post = {}

    audit_log = await audit(pre, post, request)

    assert pre == {}
    assert post == {}

    memoriam.domain.triggers.AUDIT_LOG_DB = True
    memoriam.domain.triggers.AUDIT_VERSIONING = True
    request.headers = {'x-authly-entity-id': 'test'}
    pre = {
        '_id': 'test/1',
        '_key': '1',
        'updated': 'now',
        'test': 'test',
        'more': 'more'
    }
    post = {
        '_id': 'test/1',
        '_key': '1',
        'updated': 'later',
        'test': 'test',
        'more': 'less'
    }

    await audit(pre, post, request)

    query = db.aql.call_args_list[0][0][0]

    assert '"created":"later"' in query
    assert '"creator":"test"' in query
    assert '"operation":"update"' in query
    assert '"pre":{"more":"more"}' in query
    assert '"post":{"more":"less"}' in query

    query = db.aql.call_args_list[1][0][0]

    assert 'UPDATE "1"' in query
    assert '"_version": "audit_log/1"' in query
