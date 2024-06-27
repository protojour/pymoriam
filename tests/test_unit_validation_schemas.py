from pathlib import Path


import jsonschema_rs as jsrs
from memoriam.utils import load_yaml


def test_db_schema_validation():
    validation_schema_path = Path(__file__, '..', '..', 'memoriam', 'data', 'db_schema_validation_schema.yml').resolve()
    validation_schema = load_yaml(path=validation_schema_path)

    to_validate_path = Path(__file__, '..', '..', 'memoriam', 'data', 'db_schema.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None

    to_validate_path = Path(__file__, '..', '..', 'memoriam', 'data', 'db_schema_audit.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None

    to_validate_path = Path(__file__, '..', '..', 'memoriam', 'data', 'db_schema_domain.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None

    to_validate_path = Path(__file__, '..', 'data', 'test_schema_integration.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None


def test_domain_schema_validation():
    validation_schema_path = Path(__file__, '..', '..', 'memoriam', 'data', 'domain_schema_validation_schema.yml').resolve()
    validation_schema = load_yaml(path=validation_schema_path)

    domain_path = Path(__file__, '..', 'data', 'test_domain_infoflow.yml').resolve()
    domain = load_yaml(path=domain_path)
    schema = domain.get('schema', '')
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None


def test_index_config_validation():
    validation_schema_path = Path(__file__, '..', '..', 'memoriam', 'data', 'index_config_validation_schema.yml').resolve()
    validation_schema = load_yaml(path=validation_schema_path)

    to_validate_path = Path(__file__, '..', '..', 'memoriam', 'data', 'index_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None

    to_validate_path = Path(__file__, '..', 'data', 'test_index_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None


def test_logging_config_validation():
    validation_schema_path = Path(__file__, '..', '..', 'memoriam', 'data', 'logging_config_validation_schema.yml').resolve()
    validation_schema = load_yaml(path=validation_schema_path)

    to_validate_path = Path(__file__, '..', '..', 'memoriam', 'data', 'logging_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None

    to_validate_path = Path(__file__, '..', 'data', 'test_logging_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None


def test_search_config_validation():
    validation_schema_path = Path(__file__, '..', '..', 'memoriam', 'data', 'search_config_validation_schema.yml').resolve()
    validation_schema = load_yaml(path=validation_schema_path)

    to_validate_path = Path(__file__, '..', '..', 'memoriam', 'data', 'search_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None

    to_validate_path = Path(__file__, '..', 'data', 'test_search_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None


def test_service_config_validation():
    validation_schema_path = Path(__file__, '..', '..', 'memoriam', 'data', 'service_config_validation_schema.yml').resolve()
    validation_schema = load_yaml(path=validation_schema_path)

    to_validate_path = Path(__file__, '..', '..', 'memoriam', 'data', 'service_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None

    to_validate_path = Path(__file__, '..', 'data', 'test_service_config.yml').resolve()
    schema = load_yaml(path=to_validate_path)
    assert jsrs.JSONSchema(validation_schema).validate(schema) is None
