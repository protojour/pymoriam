
import pytest

from sanic.exceptions import InvalidUsage

from memoriam.arangodb import *


def test_get_all_collections():
    schema = {}
    assert get_all_collections(schema) == ''

    schema = {
        'bad schema': 'nothing here'
    }
    assert get_all_collections(schema) == ''

    schema = {
        'collections': {
            'test_collection': {}
        },
        'edge_collections': {
            'test_edge_collection': {}
        }
    }
    assert get_all_collections(schema) == 'test_collection, test_edge_collection'


@pytest.fixture()
def domain_spec():
    return {
        'test a': {
            'label': 'Test name',
            'description': 'Test description',
            'resolver': 'coll_a',
            'attributes': {
                'field_a': 'field'
            },
            'relations': {
                'rel_a': [['ANY'], 'origin', 'outbound'],
                'rel_b': [['test b'], 'origin', 'inbound'],
                'rel_c': ['ANY', 'origin', 'any'],
                'rel_d': ['test b', 'origin', 'any'],
            }
        },
        'test b': {
            'label': 'Test name 2',
            'description': 'Test description 2',
            'resolver': 'coll_b',
            'attributes': {
                'field_b': 'field'
            },
            'relations': {
                'rel_e': ['test b', 'origin', 'any']
            }
        }
    }


def test_get_relation_attributes(domain_spec):
    class_spec = domain_spec['test a']
    relation = 'rel_a'
    result = get_relation_attributes(domain_spec, class_spec, relation)
    assert result == {
        'field_a': 'field',
        'field_b': 'field'
    }

    relation = 'rel_b'
    result = get_relation_attributes(domain_spec, class_spec, relation)
    assert result == {
        'field_b': 'field'
    }

    relation = 'rel_c'
    result = get_relation_attributes(domain_spec, class_spec, relation)
    assert result == {
        'field_a': 'field',
        'field_b': 'field'
    }

    relation = 'rel_d'
    result = get_relation_attributes(domain_spec, class_spec, relation)
    assert result == {
        'field_b': 'field'
    }


def test_get_relation_relations(domain_spec):
    class_spec = domain_spec['test a']
    relation = 'rel_a'
    result = get_relation_relations(domain_spec, class_spec, relation)
    assert result == {
        'rel_a': [['ANY'], 'origin', 'outbound'],
        'rel_b': [['test b'], 'origin', 'inbound'],
        'rel_c': ['ANY', 'origin', 'any'],
        'rel_d': ['test b', 'origin', 'any'],
        'rel_e': ['test b', 'origin', 'any']
    }

    relation = 'rel_b'
    result = get_relation_relations(domain_spec, class_spec, relation)
    assert result == domain_spec['test b']['relations']

    relation = 'rel_c'
    result = get_relation_relations(domain_spec, class_spec, relation)
    assert result == {
        'rel_a': [['ANY'], 'origin', 'outbound'],
        'rel_b': [['test b'], 'origin', 'inbound'],
        'rel_c': ['ANY', 'origin', 'any'],
        'rel_d': ['test b', 'origin', 'any'],
        'rel_e': ['test b', 'origin', 'any']
    }

    relation = 'rel_d'
    result = get_relation_relations(domain_spec, class_spec, relation)
    assert result == domain_spec['test b']['relations']


def test_get_edge_attributes(domain_spec):
    db_schema = {
        'collections': {
            'coll_a': {}
        },
        'edge_collections': {
            'origin': {
                'properties': {
                    'edge_prop_a': {
                        'type': 'string'
                    },
                    'edge_prop_b': {
                        'type': 'string'
                    },
                }
            }
        }
    }
    edge_attributes = get_edge_attributes(db_schema, domain_spec['test a'], 'rel_a')
    assert edge_attributes == {
        'edge_prop_a': 'edge_prop_a',
        'edge_prop_b': 'edge_prop_b'
    }


def test_get_type_filters(domain_spec):
    edge_spec = 'ANY'
    result = get_type_filters(domain_spec, edge_spec)
    assert result == ''

    edge_spec = ['TestA']
    result = get_type_filters(domain_spec, edge_spec)
    assert result == 'FILTER IS_SAME_COLLECTION("coll_a", object)'

    edge_spec = ['test_a', 'test_b']
    result = get_type_filters(domain_spec, edge_spec)
    assert result == 'FILTER IS_SAME_COLLECTION("coll_a", object) OR IS_SAME_COLLECTION("coll_b", object)'


def test_get_filter_strings():
    attributes = {}
    filter_query = []
    bind_vars = {}
    result = get_filter_strings(filter_query, attributes, bind_vars)
    assert result == ''
    assert bind_vars == {}

    attributes = {
        'field_a': 'field_x',
        'field_b': 'field_y',
    }
    filter_query = [
        'field_a == 5',
        'field_a != 1',
        'field_a < 5',
        'field_a <= 3',
        'field_a > 3',
        'field_a >= 3',
        'field_a IN [1, 2, 3]',
        'field_a NOTIN [4, 5]',
        'field_b LIKE "prefix%"',
        'field_b NOTLIKE "%suffix"',
        'field_b =~ "prefix%"',
        'field_b !~ "%suffix"',
    ]
    bind_vars = {}
    result = get_filter_strings(filter_query, attributes, bind_vars)
    assert 'FILTER object.field_x == @object_field_x_comp_1' in result
    assert 'FILTER object.field_x != @object_field_x_comp_2' in result
    assert 'FILTER object.field_x < @object_field_x_comp_3' in result
    assert 'FILTER object.field_x <= @object_field_x_comp_4' in result
    assert 'FILTER object.field_x > @object_field_x_comp_5' in result
    assert 'FILTER object.field_x >= @object_field_x_comp_6' in result
    assert 'FILTER object.field_x IN @object_field_x_comp_7' in result
    assert 'FILTER object.field_x NOT IN @object_field_x_comp_8' in result
    assert 'FILTER object.field_y LIKE @object_field_y_comp_9' in result
    assert 'FILTER object.field_y NOT LIKE @object_field_y_comp_10' in result
    assert 'FILTER object.field_y =~ @object_field_y_comp_11' in result
    assert 'FILTER object.field_y !~ @object_field_y_comp_12' in result
    assert bind_vars.get('object_field_x_comp_1') == 5
    assert bind_vars.get('object_field_x_comp_2') == 1
    assert bind_vars.get('object_field_x_comp_3') == 5
    assert bind_vars.get('object_field_x_comp_4') == 3
    assert bind_vars.get('object_field_x_comp_5') == 3
    assert bind_vars.get('object_field_x_comp_6') == 3
    assert bind_vars.get('object_field_x_comp_7') == [1, 2, 3]
    assert bind_vars.get('object_field_x_comp_8') == [4, 5]
    assert bind_vars.get('object_field_y_comp_9') == 'prefix%'
    assert bind_vars.get('object_field_y_comp_10') == '%suffix'
    assert bind_vars.get('object_field_y_comp_11') == 'prefix%'
    assert bind_vars.get('object_field_y_comp_12') == '%suffix'

    with pytest.raises(InvalidUsage):
        filter_query = [
            'field_c == 1',
        ]
        bind_vars = {}
        result = get_filter_strings(filter_query, attributes, bind_vars)

    with pytest.raises(InvalidUsage):
        filter_query = [
            'field_a === 1',
        ]
        bind_vars = {}
        result = get_filter_strings(filter_query, attributes, bind_vars)

    with pytest.raises(InvalidUsage):
        filter_query = [
            'field_a NOT IN [1]',
        ]
        bind_vars = {}
        result = get_filter_strings(filter_query, attributes, bind_vars)


def test_get_field_spec():
    attributes = {}
    fields_query = []
    bind_vars = {}
    result = get_field_spec(fields_query, attributes, bind_vars)
    assert result == 'object'
    assert bind_vars == {}

    attributes = {
        'field_a': 'field_x',
        'field_b': 'field_y',
    }
    fields_query = ['field_a']
    bind_vars = {}
    result = get_field_spec(fields_query, attributes, bind_vars)
    assert '@object_field_x_key: object.field_x' in result
    assert bind_vars.get('object_field_x_key') == 'field_a'

    fields_query = ['field_a', 'field_b']
    bind_vars = {}
    result = get_field_spec(fields_query, attributes, bind_vars)
    assert '@object_field_x_key: object.field_x' in result
    assert '@object_field_y_key: object.field_y' in result
    assert bind_vars.get('object_field_x_key') == 'field_a'
    assert bind_vars.get('object_field_y_key') == 'field_b'

    with pytest.raises(InvalidUsage):
        fields_query = ['field_none']
        bind_vars = {}
        result = get_field_spec(fields_query, attributes, bind_vars)


def test_get_sort_string():
    attributes = {
        'field_a': 'field_x',
        'field_b': 'field_y',
    }
    sort_query = []
    result = get_sort_string(sort_query, attributes)
    assert result == ''

    sort_query = ['field_a']
    result = get_sort_string(sort_query, attributes)
    assert result == 'SORT object.field_x, object._key'

    sort_query = ['-field_b', 'field_a']
    result = get_sort_string(sort_query, attributes, obj_name='sub_object')
    assert result == 'SORT sub_object.field_y DESC, sub_object.field_x, sub_object._key'

    with pytest.raises(InvalidUsage):
        sort_query = ['field_c']
        result = get_sort_string(sort_query, attributes)


@pytest.fixture()
def ast_dict():
    return {
        'kind': 'operation_definition',
        'name': None,
        'directives': [],
        'variable_definitions': [],
        'selection_set': {
            'kind': 'selection_set',
            'selections': [
                {
                    'kind': 'field',
                    'directives': [],
                    'alias': None,
                    'name': {
                        'kind': 'name',
                        'value': 'MitreAttck'
                    },
                    'arguments': [],
                    'selection_set': {
                        'kind': 'selection_set',
                        'selections': [
                            {
                                'kind': 'field',
                                'directives': [],
                                'alias': None,
                                'name': {
                                    'kind': 'name',
                                    'value': 'TacticList'
                                },
                                'arguments': [],
                                'selection_set': {
                                    'kind': 'selection_set',
                                    'selections': [
                                        {
                                            'kind': 'field',
                                            'directives': [],
                                            'alias': None,
                                            'name': {
                                                'kind': 'name',
                                                'value': 'results'
                                            },
                                            'arguments': [],
                                            'selection_set': {
                                                'kind': 'selection_set',
                                                'selections': [
                                                    {
                                                        'kind': 'field',
                                                        'directives': [],
                                                        'alias': None,
                                                        'name': {
                                                            'kind': 'name',
                                                            'value': 'id'
                                                        },
                                                        'arguments': [],
                                                        'selection_set': None
                                                    },
                                                    {
                                                        'kind': 'field',
                                                        'directives': [],
                                                        'alias': None,
                                                        'name': {
                                                            'kind': 'name',
                                                            'value': 'name'
                                                        },
                                                        'arguments': [],
                                                        'selection_set': None
                                                    },
                                                    {
                                                        'kind': 'field',
                                                        'directives': [],
                                                        'alias': None,
                                                        'name': {
                                                            'kind': 'name',
                                                            'value': 'description'
                                                        },
                                                        'arguments': [],
                                                        'selection_set': None
                                                    },
                                                    {
                                                        'kind': 'field',
                                                        'directives': [],
                                                        'alias': None,
                                                        'name': {
                                                            'kind': 'name',
                                                            'value': 'techniques'
                                                        },
                                                        'arguments': [
                                                            {
                                                                'kind': 'argument',
                                                                'name': {
                                                                    'kind': 'name',
                                                                    'value': 'filters'
                                                                },
                                                                'value': {
                                                                    'kind': 'list_value',
                                                                    'values': [
                                                                        {
                                                                            'kind': 'string_value',
                                                                            'value': 'x_mitre_is_subtechnique == false',
                                                                            'block': False
                                                                        }
                                                                    ]
                                                                }
                                                            }
                                                        ],
                                                        'selection_set': {
                                                            'kind': 'selection_set',
                                                            'selections': [
                                                                {
                                                                    'kind': 'field',
                                                                    'directives': [],
                                                                    'alias': None,
                                                                    'name': {
                                                                        'kind': 'name',
                                                                        'value': 'results'
                                                                    },
                                                                    'arguments': [],
                                                                    'selection_set': {
                                                                        'kind': 'selection_set',
                                                                        'selections': [
                                                                            {
                                                                                'kind': 'field',
                                                                                'directives': [],
                                                                                'alias': None,
                                                                                'name': {
                                                                                    'kind': 'name',
                                                                                    'value': 'id'
                                                                                },
                                                                                'arguments': [],
                                                                                'selection_set': None
                                                                            },
                                                                            {
                                                                                'kind': 'field',
                                                                                'directives': [],
                                                                                'alias': None,
                                                                                'name': {
                                                                                    'kind': 'name',
                                                                                    'value': 'name'
                                                                                },
                                                                                'arguments': [],
                                                                                'selection_set': None
                                                                            },
                                                                            {
                                                                                'kind': 'field',
                                                                                'directives': [],
                                                                                'alias': None,
                                                                                'name': {
                                                                                    'kind': 'name',
                                                                                    'value': 'description'
                                                                                },
                                                                                'arguments': [],
                                                                                'selection_set': None
                                                                            },
                                                                            {
                                                                                'kind': 'field',
                                                                                'directives': [],
                                                                                'alias': None,
                                                                                'name': {
                                                                                    'kind': 'name',
                                                                                    'value': 'subtechniques'
                                                                                },
                                                                                'arguments': [
                                                                                    {
                                                                                        'kind': 'argument',
                                                                                        'name': {
                                                                                            'kind': 'name',
                                                                                            'value': 'filters'
                                                                                        },
                                                                                        'value': {
                                                                                            'kind': 'list_value',
                                                                                            'values': [
                                                                                                {
                                                                                                    'kind': 'string_value',
                                                                                                    'value': 'x_mitre_is_subtechnique == true',
                                                                                                    'block': False
                                                                                                }
                                                                                            ]
                                                                                        }
                                                                                    },
                                                                                    {
                                                                                        'kind': 'argument',
                                                                                        'name': {
                                                                                            'kind': 'name',
                                                                                            'value': 'limit'
                                                                                        },
                                                                                        'value': {
                                                                                            'kind': 'int_value',
                                                                                            'value': '10'
                                                                                        }
                                                                                    }
                                                                                ],
                                                                                'selection_set': {
                                                                                    'kind': 'selection_set',
                                                                                    'selections': [
                                                                                        {
                                                                                            'kind': 'field',
                                                                                            'directives': [],
                                                                                            'alias': None,
                                                                                            'name': {
                                                                                                'kind': 'name',
                                                                                                'value': 'results'
                                                                                            },
                                                                                            'arguments': [],
                                                                                            'selection_set': {
                                                                                                'kind': 'selection_set',
                                                                                                'selections': [
                                                                                                    {
                                                                                                        'kind': 'field',
                                                                                                        'directives': [],
                                                                                                        'alias': None,
                                                                                                        'name': {
                                                                                                            'kind': 'name',
                                                                                                            'value': 'id'
                                                                                                        },
                                                                                                        'arguments': [],
                                                                                                        'selection_set': None
                                                                                                    },
                                                                                                    {
                                                                                                        'kind': 'field',
                                                                                                        'directives': [],
                                                                                                        'alias': None,
                                                                                                        'name': {
                                                                                                            'kind': 'name',
                                                                                                            'value': 'name'
                                                                                                        },
                                                                                                        'arguments': [],
                                                                                                        'selection_set': None
                                                                                                    },
                                                                                                    {
                                                                                                        'kind': 'field',
                                                                                                        'directives': [],
                                                                                                        'alias': None,
                                                                                                        'name': {
                                                                                                            'kind': 'name',
                                                                                                            'value': 'description'
                                                                                                        },
                                                                                                        'arguments': [],
                                                                                                        'selection_set': None
                                                                                                    }
                                                                                                ]
                                                                                            }
                                                                                        }
                                                                                    ]
                                                                                }
                                                                            }
                                                                        ]
                                                                    }
                                                                }
                                                            ]
                                                        }
                                                    }
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        },
        'operation': 'query'
    }


def test_get_ast_subtree(ast_dict):
    result = get_ast_subtree(ast_dict, 'MitreAttck')
    assert result == ast_dict['selection_set']['selections'][0]

    result = get_ast_subtree(ast_dict, 'TacticList')
    assert result == ast_dict['selection_set']['selections'][0]['selection_set']['selections'][0]

    subresult = get_ast_subtree(result, 'techniques')
    assert subresult == result['selection_set']['selections'][0]['selection_set']['selections'][3]


def test_get_ast_fields(ast_dict):
    subdict = get_ast_subtree(ast_dict, 'MitreAttck')
    result = get_ast_fields(subdict)
    assert result == ['TacticList']

    subdict = get_ast_subtree(ast_dict, 'TacticList')
    result = get_ast_fields(subdict)
    assert result == ['id', 'name', 'description', 'techniques']

    subdict = get_ast_subtree(subdict, 'techniques')
    result = get_ast_fields(subdict)
    assert result == ['id', 'name', 'description', 'subtechniques']


def test_cast_argument():
    argument = {
        'kind': 'argument',
        'value': {
            'kind': 'list_value',
            'values': [
                {
                    'kind': 'string_value',
                    'value': 'test'
                }
            ]
        }
    }
    result = cast_argument(argument)
    assert result == ['test']

    argument = {
        'kind': 'argument',
        'value': {
            'kind': 'int_value',
            'value': '100'
        }
    }
    result = cast_argument(argument)
    assert result == 100


def test_get_ast_arguments():
    ast_dict = {
        'arguments': [
            {
                'kind': 'argument',
                'name': {
                    'kind': 'name',
                    'value': 'filters'
                },
                'value': {
                    'kind': 'list_value',
                    'values': [
                        {
                            'kind': 'string_value',
                            'value': 'x_mitre_is_subtechnique == true',
                            'block': False
                        }
                    ]
                }
            },
            {
                'kind': 'argument',
                'name': {
                    'kind': 'name',
                    'value': 'limit'
                },
                'value': {
                    'kind': 'int_value',
                    'value': '10'
                }
            },
            {
                'kind': 'argument',
                'name': {
                    'kind': 'name',
                    'value': 'limit'
                },
                'value': {
                    'kind': 'int_value',
                    'value': '10'
                }
            }
        ]
    }
    variables = {

    }
    result = get_ast_arguments(ast_dict, variables)
    assert result == {
        'filters': ['x_mitre_is_subtechnique == true'],
        'limit': 10,
    }


def test_get_return_spec():
    subqueries = []
    result = get_return_spec(subqueries)
    assert result == 'object'

    subqueries = [
        'some_query: (test)',
        'another_query: (test)'
    ]
    result = get_return_spec(subqueries, obj_name='test', _edge=True)
    assert result == '''
    MERGE(
        test,
        {_edge: UNSET(test_edge, "_id", "_key", "_rev", "_from", "_to")},
        {
            some_query: (test), another_query: (test)
        }
    )'''


def test_get_subqueries(ast_dict):
    db_schema = {}
    domain_spec = {}
    relations = []
    variables = {}
    bind_vars = {}
    result = get_subqueries(db_schema, None, None, ast_dict, relations, variables, bind_vars)
    assert result == []

    db_schema = {}
    domain_spec = {}
    relations = []
    variables = {}
    bind_vars = {}
    result = get_subqueries(db_schema, None, None, ast_dict, relations, variables, bind_vars)
    assert result == []


def test_get_dotted_queries():
    selection = [
        'a',
        'b',
        'c == "something"',
        'sub1.c',
        'sub1.d',
        'sub1.sub2.e',
        'sub1.sub2.f',
        'filter1.c == "something"',
    ]
    subject = ''
    sublevel = 0
    result = get_dotted_queries(selection, subject, sublevel)
    assert result == ['a', 'b', 'c == "something"']

    subject = 'sub1'
    sublevel = 1
    result = get_dotted_queries(selection, subject, sublevel)
    assert result == ['c', 'd']

    subject = 'sub2'
    sublevel = 2
    result = get_dotted_queries(selection, subject, sublevel)
    assert result == ['e', 'f']

    subject = 'filter1'
    sublevel = 1
    result = get_dotted_queries(selection, subject, sublevel)
    assert result == ['c == "something"']


def test_get_diffs():
    pre = {
        '_id': 'test/1',
        '_key': '1',
        '_rev': 'abc',
        '_index': 'me test more',
        'creator': 'me',
        'created': 'now',
        'updated': 'now',
        'test': 'test',
        'more': 'more',
        'list': [1, 2, 3],
        'static': 'still',
        'list_with_dict': [{'foo': 'bar'}]
    }
    post = {
        '_id': 'test/1',
        '_key': '1',
        '_rev': 'def',
        '_index': 'me work less',
        'creator': 'me',
        'created': 'now',
        'updated': 'later',
        'test': 'work',
        'more': 'less',
        'list': [1, 2, 3],
        'static': 'still',
        'list_with_dict': [{'foo': 'bar'}]
    }

    pre_diff, post_diff = get_diffs(pre, post)

    assert pre_diff == {
        'test': 'test',
        'more': 'more',
    }
    assert post_diff == {
        'test': 'work',
        'more': 'less',
    }


def test_set_defaults():
    db_schema = {
        'collections': {
            'test': {
                'properties': {
                    'field_x': {
                        'default': 'default'
                    }
                }
            }
        }
    }
    data = {
        'field_y': 'data'
    }
    result = set_defaults(data, 'test', db_schema)
    assert result == {
        'field_x': 'default',
        'field_y': 'data',
    }


def test_translate_input():
    obj = {
        'attributes': {
            'field_a': 'field_x',
            'field_b': 'field_y',
        }
    }
    data = {
        '_id': 'test/1',
        '_key': '1',
        'field_a': 'test',
        'field_b': 'data',
        'field_c': 'hidden',
    }
    result = translate_input(data, obj)
    assert result == {
        'field_x': 'test',
        'field_y': 'data',
    }

    obj['permissive'] = 'input'  # type: ignore
    result = translate_input(data, obj)
    assert result == {
        'field_x': 'test',
        'field_y': 'data',
        'field_c': 'hidden',
    }


def test_translate_output():
    obj = {
        'attributes': {
            'field_a': 'field_x',
            'field_b': 'field_y',
        }
    }
    data = {
        '_id': 'test/1',
        '_key': '1',
        '_class': 'test',
        'field_x': 'test',
        'field_y': 'data',
        'field_z': 'hidden',
        '_edge': {
            'edge_field': 'test'
        }
    }
    result = translate_output(data, obj)
    assert result == {
        '_key': '1',
        '_class': 'test',
        'field_a': 'test',
        'field_b': 'data',
    }

    obj['permissive'] = 'output'  # type: ignore
    result = translate_output(data, obj)
    assert result == {
        '_key': '1',
        '_class': 'test',
        'field_a': 'test',
        'field_b': 'data',
        'field_z': 'hidden',
        '_edge': {
            'edge_field': 'test'
        }
    }
