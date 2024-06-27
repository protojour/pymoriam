from unittest.mock import MagicMock


from caseconverter import snakecase, camelcase, pascalcase
from sanic.request import Request
from memoriam.utils import *


def test_trueish():
    assert trueish(True)
    assert trueish('True')
    assert trueish('true')
    assert trueish('yes')
    assert trueish('on')
    assert trueish('1')
    assert trueish(1)
    assert not trueish(False)
    assert not trueish('False')
    assert not trueish('false')
    assert not trueish('no')
    assert not trueish('off')
    assert not trueish('0')
    assert not trueish(0)


def test_iso8601_now():
    timestamp = iso8601_now()
    assert len(timestamp) == 27
    assert timestamp[-1] == 'Z'
    assert timestamp[:2] == '20'  # time travel safeguard


def test_get_user_id():
    request = MagicMock(Request)
    request.headers = {'x-authly-entity-id': 'test'}
    assert get_user_id(request) == 'test'


def test_scrub_headers():
    headers = {'test': 'header'}
    result = scrub_headers(headers)
    assert result == headers

    headers = {
        'test': 'header',
        'transfer-encoding': 'chunked',
    }
    result = scrub_headers(headers)
    assert 'test' in result
    assert 'transfer-encoding' not in result

    headers = {
        'test': 'header',
        'content-length': '1000000'
    }
    result = scrub_headers(headers)
    assert 'test' in result
    assert 'content-length' not in result


def test_load_raw():
    path = './tests/data/test_spec_unit.yml'
    yaml = load_raw(path)
    assert 'openapi: 3.1.0' in yaml


def test_load_yaml():
    data = 'openapi: 3.1.0'
    data = load_yaml(data)
    assert data['openapi'] == '3.1.0'

    path = './tests/data/test_spec_unit.yml'
    data = load_yaml(path=path)
    assert data['openapi'] == '3.1.0'


def test_class_to_typename():
    obj = None
    assert class_to_typename(obj) is obj

    obj = {}
    assert class_to_typename(obj) is obj

    obj = {'_class': 'test'}
    assert class_to_typename(obj) == {'__typename': 'Test'}


def test_validate_iso8601():
    dt = '1984'
    result = validate_iso8601(dt)
    assert result == Undefined

    dt = '1970-01-01T00:00:00.000Z'
    result = validate_iso8601(dt)
    assert result == dt

    dt = '1970-01-01T00:00:00.000000Z'
    result = validate_iso8601(dt)
    assert result == dt


def test_caseconverter():
    # test expectations for the caseconverter library
    assert snakecase('test') == 'test'
    assert snakecase('Test') == 'test'
    assert snakecase('TEST') == 'test'
    assert snakecase('this is a test') == 'this_is_a_test'
    assert snakecase('This... is a TEST') == 'this_is_a_test'

    assert camelcase('test') == 'test'
    assert camelcase('Test') == 'test'
    assert camelcase('TEST') == 'test'
    assert camelcase('this is a test') == 'thisIsATest'
    assert camelcase('This... is a TEST') == 'thisIsATest'

    assert pascalcase('test') == 'Test'
    assert pascalcase('Test') == 'Test'
    assert pascalcase('TEST') == 'Test'
    assert pascalcase('this is a test') == 'ThisIsATest'
    assert pascalcase('This... is a TEST') == 'ThisIsATest'
