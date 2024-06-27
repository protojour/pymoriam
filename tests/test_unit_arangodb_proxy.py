from unittest.mock import MagicMock


import memoriam.storage.arango_proxy
from memoriam.storage.arango_proxy import *


def test_get_arangodb_host():

    memoriam.storage.arango_proxy.ARANGO_HOSTS = 'test1,test2,test3'

    class PatchedArangoProxy(ArangoProxy):
        init_arangodb = MagicMock()

    arango_proxy = PatchedArangoProxy(MagicMock())

    assert next(arango_proxy.host_iterator) == 'test1'
    assert next(arango_proxy.host_iterator) == 'test2'
    assert next(arango_proxy.host_iterator) == 'test3'
    assert next(arango_proxy.host_iterator) == 'test1'
    assert next(arango_proxy.host_iterator) == 'test2'
    assert next(arango_proxy.host_iterator) == 'test3'
    assert next(arango_proxy.host_iterator) == 'test1'
    assert next(arango_proxy.host_iterator) == 'test2'
    assert next(arango_proxy.host_iterator) == 'test3'
