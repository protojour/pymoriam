import pytest

from memoriam.domain.domain import validate_domain_schema
from memoriam.utils import load_yaml


def test_validate_domain_schema():
    with pytest.raises(ValueError, match='Domain schema should be a map'):
        validate_domain_schema(load_yaml('''

        - Test

        '''))

    with pytest.raises(ValueError, match='"name" should be a string'):
        validate_domain_schema(load_yaml('''

        1: {}

        '''))

    with pytest.raises(ValueError, match='"description" should be a string'):
        validate_domain_schema(load_yaml('''

        test: {}

        '''))

    with pytest.raises(ValueError, match='"resolver" should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema

        '''))

    with pytest.raises(ValueError, match='"resolver" should be in backend schema'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: test

        '''))

    with pytest.raises(ValueError, match='"permissive" should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: true

        '''))

    with pytest.raises(ValueError, match='"attributes" should be a map'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: both
            attributes: test

        '''))

    with pytest.raises(ValueError, match='"relations" should be a map'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: input
            attributes: {}
            relations: test

        '''))

    with pytest.raises(ValueError, match='Constant name should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: output
            constants:
                1: 2
            relations: {}

        '''))

    with pytest.raises(ValueError, match='Constant value should be of type string, int, float or bool'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: no
            constants:
                test_constant: [test]
            relations: {}

        '''))

    with pytest.raises(ValueError, match='Constant value should be of type string, int, float or bool'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: no
            constants:
                test_constant:
                    test: test
            relations: {}

        '''))

    with pytest.raises(ValueError, match='Attribute name should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: no
            constants:
                test_constant: test
            attributes:
                1: 2
            relations: {}

        '''))

    with pytest.raises(ValueError, match='Attribute resolver should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            permissive: no
            constants:
                test_constant: 1
            attributes:
                test_field: 1
            relations: {}

        '''))

    with pytest.raises(ValueError, match='Attribute resolver should be in backend schema properties'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            constants:
                test_constant: true
            attributes:
                test_field: test
            relations: {}

        '''))

    with pytest.raises(ValueError, match='Relation name should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                1: test

        '''))

    with pytest.raises(ValueError, match='Relation should be a list'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: 1

        '''))

    with pytest.raises(ValueError, match='Relation should have 3 items'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [1]

        '''))

    with pytest.raises(ValueError, match='Edge items should be strings'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [[1], 2, 3]

        '''))

    with pytest.raises(ValueError, match='Edge items should be other domain classes or "ANY"'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [[foo], 2, 3]

        '''))

    with pytest.raises(ValueError, match='Edge type should be a string or list of strings'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [1, 2, 3]

        '''))

    with pytest.raises(ValueError, match='Edge type\(s\) should be other domain classes or "ANY"'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [foo, 2, 3]

        '''))

    with pytest.raises(ValueError, match='Edge collection should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, 2, 3]

        '''))

    with pytest.raises(ValueError, match='Edge collection should be in backend schema'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, test, 3]

        '''))

    with pytest.raises(ValueError, match=r'Edge \(depth/\)direction should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, 3]

        '''))

    with pytest.raises(ValueError, match='Edge direction should be "outbound", "inbound", or "any"'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, test]

        '''))

    with pytest.raises(ValueError, match='Optional traversal depth should correspond to'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, any outbound]

        '''))

    with pytest.raises(ValueError, match='Optional traversal depth should correspond to'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, MIN outbound]

        '''))

    with pytest.raises(ValueError, match='Optional traversal depth should correspond to'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, 1..MAX outbound]

        '''))

    with pytest.raises(ValueError, match='Optional traversal depth should correspond to'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, 1.2 outbound]

        '''))

    with pytest.raises(ValueError, match='"triggers" should be a list'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, 1..2 outbound]
            triggers: test

        '''))

    with pytest.raises(ValueError, match='Trigger should be a string'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, 1 outbound]
            triggers:
                - 123

        '''))

    with pytest.raises(ValueError, match='Triggers should be one of the following'):
        validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, outbound]
            triggers:
                - set_created
                - test

        '''))

    with pytest.raises(ValueError, match='Domain schema contains colliding class names'):
        validate_domain_schema(load_yaml('''

        test_a:
            description: Test schema
            resolver: entity
            attributes: {}

        Test_A:
            description: Test schema
            resolver: entity
            attributes: {}

        '''))

    assert validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [ANY, includes, outbound]
            triggers:
                - set_created

    '''))

    assert validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [[ANY], includes, inbound]
            triggers:
                - set_updated

    '''))

    assert validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [test, includes, any]
            triggers:
                - set_created
                - set_updated

    '''))

    assert validate_domain_schema(load_yaml('''

        test:
            description: Test schema
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [[test], includes, outbound]
            triggers:
                - set_created
                - set_updated

    '''))

    assert validate_domain_schema(load_yaml('''

        test_a:
            description: Test schema a
            resolver: entity
            attributes:
                test_field: data
            relations:
                test_relation: [test_b, origin, outbound]
            triggers:
                - set_created
                - set_updated

        test_b:
            description: Test schema b
            resolver: entity
            attributes:
                test_field: label
            relations:
                test_relation: [[test_a, test_b], includes, outbound]
            triggers:
                - set_created
                - set_updated

    '''))
