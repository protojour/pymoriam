import pytest

from sanic import Sanic

import memoriam.config
import memoriam.domain.audit
from memoriam.openapi import OpenAPI
from memoriam.domain.audit import *


@pytest.fixture()
def app():
    app = Sanic('test_unit_audit')
    app.update_config(memoriam.config)
    app.config.AUTO_EXTEND = False
    return app


@pytest.fixture()
def openapi(app):
    spec_path = Path(__file__, '..', 'data', 'test_spec_unit.yml').resolve()
    schema_path = Path(__file__, '..', 'data', 'test_schema_unit.yml').resolve()
    return OpenAPI(app, spec_path=spec_path, schema_path=schema_path)


def test_auditlog_init(app, openapi):

    memoriam.domain.audit.AUDIT_LOG_DB = False

    AuditLog(app, openapi)

    assert app.router.find_route_by_view_name('get_audit_log') is None
    assert app.router.find_route_by_view_name('post_audit_log') is None

    # memoriam.domain.audit.AUDIT_LOG_DB = True

    # AuditLog(app, openapi)

    # assert app.router.find_route_by_view_name('get_audit_log')
    # assert app.router.find_route_by_view_name('post_audit_log')
