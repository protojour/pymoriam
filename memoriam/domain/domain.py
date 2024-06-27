import logging
import os
import re
from pathlib import Path

import ujson as json
import yaml

from caseconverter import snakecase, pascalcase
from sanic import response
from sanic.exceptions import SanicException, InvalidUsage, NotFound

from memoriam.config import ARANGO_DOMAIN_DB_NAME, ARANGO_SCHEMA_PATH, NO_DELETE, RELOAD_SCHEMAS
from memoriam.constants import OPERATIONS
from memoriam.arangodb import get_arangodb, prettify_aql

from memoriam.utils import iso8601_now, load_raw, load_yaml


logger = logging.getLogger('memoriam')

GATEWAY_URL = 'https://memoriam-gateway:5001'
AUTHLY_SERVICENAME = os.getenv('AUTHLY_SERVICENAME', 'testservice')

AQL_DEPTH_REGEX = r'\d{1,2}(?:\.\.\d{1,2})?'

TRIGGER_FUNCS = [
    'set_creator',
    'set_created',
    'set_updated',
    'audit',
]


async def list_domains(request):
    """Handler for domain listing"""
    request.app.ctx.authorize(request, 'domain', 'read')

    db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)

    query = prettify_aql('''
    FOR object IN domain
        RETURN object
    ''')
    data = db.aql(query)

    for result in data.get('result', []):
        result.pop('_resources', None)

    return response.json(data.get('result', []), 200)


async def validate_domain(request, _key=None):
    """Handler for domain validation"""
    domain = request.json

    if 'label' in domain:
        if snakecase(domain['label']) in ('system', 'authly', 'onto', 'docs'):
            error = f'Domain cannot be named {domain["label"]}'
            logger.debug(f'Invalid domain: {error}')
            raise InvalidUsage(error, 400)

        collisions = await domain_label_collisions(domain['label'], exclude_key=_key)
        if collisions:
            error = 'Domain label collides with existing domains ' + ', '.join(collisions)
            logger.debug(f'Invalid domain: {error}')
            raise SanicException(error, 409)

    if 'schema' in domain:
        try:
            schema = load_yaml(domain['schema'])
            validate_domain_schema(schema)
        except (yaml.YAMLError, ValueError) as e:
            logger.debug(f'Invalid domain: {e}')
            raise InvalidUsage(str(e), 400) from None

    return response.empty(200)


async def post_domain(request):
    """Handler for domain creation"""
    request.app.ctx.authorize(request, 'domain', 'create')

    sub_response = await validate_domain(request)
    if sub_response.status > 200:
        return sub_response

    db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)
    now = iso8601_now()
    domain = request.json
    domain['_key'] = snakecase(domain.get('label'))
    domain['_resources'] = {}
    domain['created'] = now
    domain['updated'] = now

    query = prettify_aql(f'''
    INSERT {json.dumps(domain)}
    IN domain
    RETURN {{ new: NEW }}
    ''')
    result = db.aql(query)
    result = result['result'][0] if result['result'] else {}

    # domain schema cache invalidation
    if RELOAD_SCHEMAS:
        redis = request.app.ctx.redis
        await redis.delete('memoriam_graphql_schemas')
        await redis.delete('memoriam_rest_schemas')

    result['new'].pop('_resources', None)

    return response.json(result['new'], 201)


async def get_domain(request, _key):
    """Handler for domain access"""
    request.app.ctx.authorize(request, 'domain', 'read')

    db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)

    query = prettify_aql('''
    RETURN DOCUMENT(@_id)
    ''')
    bind_vars = {'_id': f'domain/{_key}'}
    result = db.aql(query, bind_vars=bind_vars)
    result = result['result'][0] if result['result'] else {}

    if not result:
        raise NotFound(f'domain/{_key} does not exist', 404)

    result.pop('_resources', None)

    return response.json(result, 200)


async def patch_domain(request, _key):
    """Handler for domain update"""
    request.app.ctx.authorize(request, 'domain', 'update')

    sub_response = await validate_domain(request, _key)
    if sub_response.status > 200:
        return sub_response

    db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)
    domain = request.json
    domain['updated'] = iso8601_now()

    query = prettify_aql(f'''
    UPDATE @_key WITH {json.dumps(domain)}
    IN domain
    OPTIONS {{ mergeObjects: false }}
    RETURN {{ new: NEW }}
    ''')
    bind_vars = {'_key': _key}
    result = db.aql(query, bind_vars=bind_vars)
    result = result['result'][0] if result['result'] else {}

    # domain schema cache invalidation
    if RELOAD_SCHEMAS:
        redis = request.app.ctx.redis
        await redis.delete('memoriam_graphql_schemas')
        await redis.delete('memoriam_rest_schemas')

    result['new'].pop('_resources', None)

    return response.json(result['new'], 200)


async def delete_domain(request, _key):
    """Handler for domain deletion"""
    request.app.ctx.authorize(request, 'domain', 'delete')

    if NO_DELETE:
        raise SanicException('Object deletions are disabled', 405)

    db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)

    query = prettify_aql('''
    REMOVE @_key IN domain
    ''')
    bind_vars = {'_key': _key}
    db.aql(query, bind_vars=bind_vars)

    # domain schema cache invalidation
    if RELOAD_SCHEMAS:
        redis = request.app.ctx.redis
        await redis.delete('memoriam_graphql_schemas')
        await redis.delete('memoriam_rest_schemas')

    return response.empty()


async def get_db_schema(request):
    """Handler for serving the database schema"""
    db_schema = load_raw(ARANGO_SCHEMA_PATH)

    return response.text(db_schema, 200, headers={'content-type': 'application/yaml'})


async def get_domain_validation_schema_json(request):
    """Handler for serving the domain validation schema"""
    path = Path(__file__, '..', '..', 'data', 'domain_schema_validation_schema.json').resolve()
    db_schema = load_raw(path)

    return response.text(db_schema, 200, headers={'content-type': 'application/json'})


def validate_domain_schema(schema):
    """Validate a parsed domain schema"""
    db_schema = load_yaml(path=ARANGO_SCHEMA_PATH)

    if not isinstance(schema, dict):
        raise ValueError('Domain schema should be a map')

    for name, klass in schema.items():

        description = klass.get('description')
        resolver = klass.get('resolver')
        operations = klass.get('operations', [])
        permissive = klass.get('permissive') or 'no'
        constants = klass.get('constants', {})
        attributes = klass.get('attributes', {})
        relations = klass.get('relations', {})
        triggers = klass.get('triggers', [])

        if not isinstance(name, str):
            raise ValueError(f'"name" should be a string (see {name})')

        if not isinstance(description, str):
            raise ValueError(f'"description" should be a string (see {name})')

        if not isinstance(resolver, str):
            raise ValueError(f'"resolver" should be a string (see {name})')

        if not isinstance(operations, list):
            raise ValueError(f'"operations" should be a list (see {name})')

        if not isinstance(permissive, str):
            raise ValueError(f'"permissive" should be a string (see {name})')

        if permissive not in ('no', 'input', 'output', 'both'):
            raise ValueError(f'"permissive" should be "no", "input", "output", or "both" (see {name})')

        if resolver not in db_schema['collections']:
            raise ValueError(f'"resolver" should be in backend schema (see {name})')

        if not isinstance(constants, dict):
            raise ValueError(f'"constants" should be a map (see {name})')

        if not isinstance(attributes, dict):
            raise ValueError(f'"attributes" should be a map (see {name})')

        if not isinstance(relations, dict):
            raise ValueError(f'"relations" should be a map (see {name})')

        if not isinstance(triggers, list):
            raise ValueError(f'"triggers" should be a list (see {name})')

        for field, value in constants.items():

            if not isinstance(field, str):
                raise ValueError(f'Constant name should be a string (see {name}: constants: {field})')

            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(f'Constant value should be of type string, int, float or bool (see {name}: constants: {field})')

        for field, field_resolver in attributes.items():

            if not isinstance(field, str):
                raise ValueError(f'Attribute name should be a string (see {name}: attributes: {field})')

            if not isinstance(field_resolver, str):
                raise ValueError(f'Attribute resolver should be a string (see {name}: attributes: {field})')

            if permissive == 'no':
                field_spec = db_schema['collections'].get(resolver, {}).get('properties', {})

                if field_resolver not in field_spec:
                    raise ValueError(f'Attribute resolver should be in backend schema properties (see {name}: attributes: {field})')

        for relation, relation_spec in relations.items():

            if not isinstance(relation, str):
                raise ValueError(f'Relation name should be a string (see {name}: relations: {relation})')

            if not isinstance(relation_spec, list):
                raise ValueError(f'Relation should be a list (see {name}: relations: {relation})')

            if len(relation_spec) != 3:
                raise ValueError(f'Relation should have 3 items (see {name}: relations: {relation})')

            edge_spec, edge_name, direction = relation_spec

            if isinstance(edge_spec, list):
                for item in edge_spec:

                    if not isinstance(item, str):
                        raise ValueError(f'Edge items should be strings (see {name}: relations: {relation})')

                    if item not in schema and item != 'ANY':
                        raise ValueError(f'Edge items should be other domain classes or "ANY" (see {name}: relations: {relation})')
            else:
                if not isinstance(edge_spec, str):
                    raise ValueError(f'Edge type should be a string or list of strings (see {name}: relations: {relation})')

                if edge_spec not in schema and edge_spec != 'ANY':
                    raise ValueError(f'Edge type(s) should be other domain classes or "ANY" (see {name}: relations: {relation})')

            if not isinstance(edge_name, str):
                raise ValueError(f'Edge collection should be a string (see {name}: relations: {relation})')

            if edge_name not in db_schema['edge_collections']:
                raise ValueError(f'Edge collection should be in backend schema (see {name}: relations: {relation})')

            if not isinstance(direction, str):
                raise ValueError(f'Edge (depth/)direction should be a string (see {name}: relations: {relation})')

            depth, direction = direction.split(' ') if ' ' in direction else ('', direction)

            if direction not in ('outbound', 'inbound', 'any'):
                raise ValueError(f'Edge direction should be "outbound", "inbound", or "any" (see {name}: relations: {relation})')

            if depth:
                if not re.fullmatch(AQL_DEPTH_REGEX, depth):
                    raise ValueError(f'Optional traversal depth should correspond to MIN[..MAX] (see {name}: relations: {relation})')

        for operation in operations:

            if not isinstance(operation, str):
                raise ValueError(f'Operation should be a string (see {name})')

            if operation not in OPERATIONS:
                raise ValueError(f'Operations should be one of the following: {OPERATIONS} (see {name})')

        for trigger in triggers:

            if not isinstance(trigger, str):
                raise ValueError(f'Trigger should be a string (see {name})')

            if trigger not in TRIGGER_FUNCS:
                raise ValueError(f'Triggers should be one of the following: {TRIGGER_FUNCS} (see {name})')

    collisions = domain_class_name_collisions(schema)

    if collisions:
        raise ValueError('Domain schema contains colliding class names: ' + ', '.join(collisions))

    return True


async def domain_label_collisions(label, exclude_key=None):
    """Check for colliding domain labels,
       after snakecase and pascalcase conversion"""
    db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)

    query = prettify_aql('''
    FOR object IN domain
        RETURN object
    ''')
    result = db.aql(query)

    collisions = set()
    for domain in result['result']:
        if domain['_key'] == exclude_key:
            continue
        if snakecase(label) == snakecase(domain['label']):
            collisions.add(domain['label'])
        if pascalcase(label) == pascalcase(domain['label']):
            collisions.add(domain['label'])

    return collisions


def domain_class_name_collisions(schema):
    """Check for colliding domain class names,
       after snakecase and pascalcase conversion"""
    seen = set()
    snake_dupes = set(snakecase(x) for x in schema if snakecase(x) in seen or seen.add(x))

    seen = set()
    pascal_dupes = set(pascalcase(x) for x in schema if pascalcase(x) in seen or seen.add(x))

    return snake_dupes | pascal_dupes


class Relation:
    """A fully parsed relation in the domain schema"""

    def __init__(self, label, json):
        self.label = label
        self.edge_spec = json[0]
        self.resolver = json[1]
        self.depth_start = 1
        self.depth_end = 1
        self.inbound = False
        self.outbound = False

        depth_direction = json[2]
        if match := re.match(r'([0-9]+)\.\.([0-9]+) .+', depth_direction):
            self.depth_start = int(match.group(1))
            self.depth_end = int(match.group(2))

        if 'inbound' in depth_direction:
            self.inbound = True
        if 'outbound' in depth_direction:
            self.outbound = True
        if 'any' in depth_direction:
            self.inbound = True
            self.outbound = True

    def match_edge(self, edge_resolver, is_inbound):
        if edge_resolver != self.resolver:
            return False
        if is_inbound and not self.inbound:
            return False
        if not is_inbound and not self.outbound:
            return False

        return True


def parse_relations(klass):
    """Parse relations into an array"""
    relations = klass.get('relations', {})
    out = []

    for label, spec in relations.items():
        out.append(Relation(label, spec))

    return out


def parse_all_relations(domain_spec):
    """Parse all domain relations by domain class"""
    relation_map = {}

    for domain_class, class_spec in domain_spec.items():
        relation_map[domain_class] = list(
            Relation(label, spec) for label, spec in class_spec.get('relations', {}).items()
        )

    return relation_map
