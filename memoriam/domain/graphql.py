import time
import logging

import os
from functools import partial
from inspect import isawaitable
from pathlib import Path

import ujson as json
from ariadne import ObjectType, UnionType, ScalarType, make_executable_schema, graphql
from ariadne.types import Extension
from benedict import benedict
from caseconverter import pascalcase, snakecase
from graphql import parse
from graphql.utilities import separate_operations
from sanic import response
from sanic.exceptions import NotFound

from memoriam.arangodb import (
    get_arangodb, prettify_aql, get_edge_attributes, get_relation_attributes,
    get_class_filters, get_type_filters, get_search_filter, get_filter_strings,
    get_sort_string, get_all_collections,
    defrag_ast, get_ast_subtree, get_ast_fields, get_subqueries, get_return_spec,
    set_defaults, translate_input, translate_output, add_constants
)
from memoriam.config import (
    ARANGO_DOMAIN_DB_NAME, ARANGO_SCHEMA_PATH, ARANGO_DEFAULT_LIMIT,
    NO_DELETE, ROOT_PATH, KEYPATH_SEPARATOR, AUDIT_VERSIONING, RELOAD_SCHEMAS
)
from memoriam.constants import OPERATIONS, RESERVED_FIELDS
from memoriam.domain.jinja import env as jinja_env
from memoriam.domain.rpc import pre_rpc, post_rpc, get_listeners
from memoriam.domain.triggers import set_creator, set_created, set_updated, audit
from memoriam.utils import load_raw, load_yaml, class_to_typename, validate_iso8601, task_handler


logging.getLogger('asyncio').setLevel(logging.ERROR)
logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')


GRAPHQL_TYPES = {
    'string':  'String',
    'number':  'Float',
    'integer': 'Int',
    'boolean': 'Boolean',
    'null':    'null',
}


class AllFieldsExtension(Extension):
    """GraphQL Extension allowing the use of the `_all` meta-field
       to return all fields on an object, even ones not part of the schema"""

    def __init__(self):
        self.all_fields = []

    async def resolve(self, next_, parent, info, **kwargs):
        if info.field_name == '_all':
            self.all_fields.append(info.path.as_list())
            return parent

        result = next_(parent, info, **kwargs)
        if isawaitable(result):
            return await result

        return result

    def format(self, context):
        return {
            'all_fields': self.all_fields
        }

    @staticmethod
    def post_process(result, domain_name, domain_cache):
        """Post processing should be called on full result.
           Resolves stored all_fields paths, translates output,
           and returns merged result."""
        if 'extensions' in result:
            extensions = result.pop('extensions')
            all_fields = extensions.get('all_fields', [])

            if all_fields:
                result_bdict = benedict(result, keypath_separator=KEYPATH_SEPARATOR)
                for path in reversed(all_fields):
                    raw_obj = result_bdict['data'][path]
                    if not isinstance(raw_obj, benedict):
                        logging.debug(f'{path} not found in AllFields post_process:\n {result_bdict}')
                        continue
                    raw_obj['_class'] = raw_obj.pop('__typename')
                    class_name = raw_obj['_class']
                    class_spec = domain_cache[domain_name][class_name]
                    class_spec['permissive'] = 'output'
                    obj = translate_output(raw_obj, class_spec)
                    obj = class_to_typename(obj)
                    relations = result_bdict['data'][path[:-1]]
                    if not isinstance(relations, benedict):
                        logging.debug(f'{path} not found in AllFields post_process:\n {result_bdict}')
                        continue
                    relations.pop('_all')
                    result_bdict['data'][path[:-1]] = {**obj, **relations}

                result = dict(result_bdict)

        return result


class GraphQLResolverEngine:
    """This Sanic extension transforms domain schemas to a working GraphQL API,
       and handles translation between domain data formats and backend data formats"""

    def __init__(self, app):
        self.app = app
        self.app.ctx.graphql_engine = self

        self.schemas = {}
        self.db_schema = load_yaml(path=ARANGO_SCHEMA_PATH)
        self.domain_cache = {}
        self.template = jinja_env.get_template('graphql_schema.graphql')
        self.type_resolver = {}

        app.register_listener(self.rebuild_schema, 'before_server_start')

        if RELOAD_SCHEMAS:
            app.register_middleware(self.schema_middleware, 'request')

        html_path = Path(ROOT_PATH, 'templates', 'graphiql.html').resolve()
        self.graphiql_html = load_raw(html_path)

        app.add_route(self.graphql_graphiql, '/<domain>/graphql', methods=['GET'])
        app.add_route(self.graphql_server, '/<domain>/graphql', methods=['POST'])

    async def schema_middleware(self, request):
        """Middleware to trigger a schema rebuild if necessary"""
        pid = os.getpid()
        built = await self.app.ctx.redis.sismember('memoriam_graphql_schemas', pid)
        if not built:
            await self.rebuild_schema(self.app)

    async def rebuild_schema(self, app):
        """Rebuild GraphQL SDL schema from currently stored domain schemas"""
        pid = os.getpid()
        await app.ctx.redis.sadd('memoriam_graphql_schemas', pid)

        start = time.perf_counter() * 1000
        logger.debug('Rebuilding GraphQL engine schemas...')

        db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)

        query = prettify_aql('''
        FOR object IN domain
            FILTER object.active == true && object.graphql == true
            RETURN object
        ''')
        result = db.aql(query)
        domains = result['result']

        datetime_scalar = ScalarType('DateTime', value_parser=validate_iso8601)
        allfields_scalar = ScalarType('AllFields')

        for domain in domains:

            domain.pop('_resources', None)

            domain_pathname = snakecase(domain['label'])
            domain_typename = pascalcase(domain['label'])
            domain_schema = load_yaml(domain['schema'])

            query = ObjectType('Query')
            mutation = ObjectType('Mutation')

            object_types = [query, datetime_scalar, allfields_scalar]

            mutations = False
            domain_data = {}

            # cache for resolvers
            self.domain_cache[domain_pathname] = {}

            # access by typename
            domain_schema = {pascalcase(k): v for k, v in domain_schema.items()}

            # pre-loop
            for class_typename, class_spec in domain_schema.items():

                if 'operations' not in class_spec:
                    domain_schema[class_typename]['operations'] = OPERATIONS

            # domain data for template
            domain_data[domain_typename] = {
                'description': domain['description'],
                'classes': {},
                'unions': {},
                'types': {},
                'edge_attributes': {},
            }

            resolver = self.get_field_resolver('version')
            query.set_field('version', resolver)

            # collect edge attributes in a generic ObjectType to be used when traversing relations
            edge_type = ObjectType('Edge')
            object_types.append(edge_type)

            resolver = self.get_field_resolver('_key')
            edge_type.set_field('_key', resolver)

            for class_typename, class_spec in domain_schema.items():

                class_name = snakecase(class_typename)

                if 'class' not in class_spec:
                    class_spec['class'] = class_name

                if 'alias' in class_spec:
                    continue

                operations = class_spec['operations']

                # cache for resolvers
                self.domain_cache[domain_pathname][class_typename] = class_spec
                self.type_resolver[class_typename] = class_spec['resolver']

                # domain data for template
                domain_data[domain_typename]['classes'][class_typename] = {
                    'description': class_spec['description'],
                    'operations': operations,
                    'attributes': {},
                    'relations': {},
                }

                # add list and single fields for each domain class to domain type
                resolver = self.get_object_resolver(domain_schema, class_name, class_spec)
                if 'read' in operations:
                    query.set_field(f'{class_typename}List', resolver)
                    query.set_field(class_typename, resolver)

                # build domain class ObjectType
                domain_class_type = ObjectType(class_typename)
                if 'read' in operations:
                    object_types.append(domain_class_type)

                resolver = self.get_field_resolver('_key')
                domain_class_type.set_field('_key', resolver)

                # all types may be target or source of a leading edge,
                # so an edge is added to each object type
                resolver = self.get_field_resolver('_edge')
                domain_class_type.set_field('_edge', resolver)

                resolver = self.get_field_resolver('_all')
                domain_class_type.set_field('_all', resolver)

                # add a wrapper ObjectType, just to return metadata on results
                domain_class_results = ObjectType(f'{class_typename}Results')
                if 'read' in operations:
                    object_types.append(domain_class_results)

                resolver = self.get_field_resolver('results_total')
                domain_class_results.set_field('results_total', resolver)

                resolver = self.get_field_resolver('results')
                domain_class_results.set_field('results', resolver)

                # add three base mutations per object
                if 'create' in operations:
                    resolver = self.get_mutation_resolver(class_name, class_spec, 'create', domain_pathname)
                    mutation.set_field(f'create{class_typename}', resolver)
                    mutations = True

                if 'update' in operations:
                    resolver = self.get_mutation_resolver(class_name, class_spec, 'update')
                    mutation.set_field(f'update{class_typename}', resolver)
                    mutations = True

                if 'delete' in operations:
                    resolver = self.get_mutation_resolver(class_name, class_spec, 'delete')
                    mutation.set_field(f'delete{class_typename}', resolver)
                    mutations = True

                # add constant fields from schema attributes
                for field_name, value in class_spec.get('constants', {}).items():

                    resolver = self.get_field_resolver(field_name)
                    domain_class_type.set_field(field_name, resolver)

                    domain_data[domain_typename]['classes'][class_typename]['attributes'][field_name] = {
                        'type': self.get_constant_type(value),
                        'is_readonly': True,
                        'description': f'Constant value: {json.dumps(value)} '
                    }

                # add regular fields from schema attributes
                for field_name, field_spec in class_spec.get('attributes', {}).items():

                    db_attr = self.db_schema['collections'][class_spec['resolver']]['properties'].get(field_spec, {})

                    if self.check_invalid_recursive(db_attr):
                        logger.warning(
                            f'{domain_typename}: {class_typename} field {field_name} is an object with no known properties, ' +
                            'or has substructures with no known properties. This is not supported by GraphQL. The field will be ignored.'
                        )
                        continue

                    if not db_attr.get('writeOnly'):
                        resolver = self.get_field_resolver(field_spec)
                        domain_class_type.set_field(field_name, resolver)

                    # add data structure for template
                    type_name = self.get_field_type(field_name, field_spec, db_attr)
                    if type_name == pascalcase(field_name):
                        type_name = f'{class_typename}{type_name}'

                    domain_data[domain_typename]['classes'][class_typename]['attributes'][field_name] = {
                        'type': type_name,
                        'is_list': db_attr.get('type') == 'array',
                        'is_readonly': db_attr.get('readOnly'),
                        'is_writeonly': db_attr.get('writeOnly'),
                        'is_required': field_spec in self.db_schema['collections'][class_spec['resolver']].get('required', []),
                        'description': db_attr.get('description')
                    }

                    # add types for document substructures
                    domain_data[domain_typename]['types'] = self.get_types_recursive(domain_data[domain_typename]['types'], type_name, db_attr)

                # add relation fields
                for field_name, relation_spec in class_spec.get('relations', {}).items():

                    edge_typename = pascalcase(field_name)
                    edge_spec, edge_name, direction = relation_spec

                    resolver = self.get_edge_resolver(domain_schema, class_spec, field_name)
                    domain_class_type.set_field(field_name, resolver)

                    # add three edge mutations per relation
                    if 'create' in operations:
                        resolver = self.get_edge_mutation_resolver(class_spec, 'attach', edge_name)
                        mutation.set_field(f'attach{class_typename}{edge_typename}Relation', resolver)
                        mutations = True

                    if 'update' in operations:
                        resolver = self.get_edge_mutation_resolver(class_spec, 'update', edge_name)
                        mutation.set_field(f'update{class_typename}{edge_typename}Relation', resolver)
                        mutations = True

                    if 'delete' in operations:
                        resolver = self.get_edge_mutation_resolver(class_spec, 'detach', edge_name)
                        mutation.set_field(f'detach{class_typename}{edge_typename}Relation', resolver)
                        mutations = True

                    # add data structure for template
                    type_name = self.get_relation_type(field_name, relation_spec, class_typename, domain_typename)
                    domain_data[domain_typename]['classes'][class_typename]['relations'][field_name] = {
                        'type': type_name,
                        'is_list': isinstance(edge_spec, list),
                        'edge_fields': {}
                    }

                    # build UnionType for each relation with multiple targets
                    if type_name[-5:] == 'Union' or type_name[-3:] == 'Any':
                        resolver = self.get_field_resolver('__typename')
                        union_type = UnionType(type_name, resolver)
                        object_types.append(union_type)

                        if type_name[-3:] == 'Any':
                            domain_data[domain_typename]['unions'][type_name] = [
                                class_name for class_name, class_spec in domain_schema.items()
                                if 'read' in class_spec['operations']
                            ]
                        else:
                            domain_data[domain_typename]['unions'][type_name] = [
                                pascalcase(class_name) for class_name in edge_spec
                            ]

                    # again, add a wrapper ObjectType, just to return metadata on results
                    edge_results = ObjectType(f'{type_name}Results')
                    object_types.append(edge_results)

                    resolver = self.get_field_resolver('results_total')
                    edge_results.set_field('results_total', resolver)

                    resolver = self.get_field_resolver('results')
                    edge_results.set_field('results', resolver)

                    # add an edge mutation per related object type
                    if type_name[-5:] == 'Union' or type_name[-3:] == 'Any':
                        for type_ in domain_data[domain_typename]['unions'][type_name]:
                            if 'create' in domain_schema[type_]['operations']:
                                resolver = self.get_edge_mutation_resolver(class_spec, 'create', edge_name,
                                    this_type=class_typename, relation_spec=relation_spec, related_type=type_, related_spec=domain_schema[type_])
                                mutation.set_field(f'create{class_typename}{edge_typename}Related{type_}', resolver)
                    else:
                        if 'create' in domain_schema[type_name]['operations']:
                            resolver = self.get_edge_mutation_resolver(class_spec, 'create', edge_name,
                                this_type=class_typename, relation_spec=relation_spec, related_type=type_name, related_spec=domain_schema[type_name])
                            mutation.set_field(f'create{class_typename}{edge_typename}Related{type_name}', resolver)

                    # add resolvers for edge attribute fields
                    for edge_field_name, db_attr in self.db_schema['edge_collections'][edge_name]['properties'].items():
                        if edge_field_name not in RESERVED_FIELDS:

                            if self.check_invalid_recursive(db_attr):
                                logger.warning(
                                    f'{domain_typename} {edge_name} edge field {edge_field_name} is an object with no known properties, ' +
                                    'or has substructures with no known properties. This is not supported by GraphQL. The field will be ignored.'
                                )
                                continue

                            # add data structure for template
                            type_name = self.get_field_type(edge_field_name, edge_field_name, db_attr)
                            domain_data[domain_typename]['edge_attributes'][edge_field_name] = type_name

                            if not db_attr.get('readOnly'):
                                resolver = self.get_field_resolver(edge_field_name)
                                edge_type.set_field(edge_field_name, resolver)

                                # add data structure for template
                                domain_data[domain_typename]['classes'][class_typename]['relations'][field_name]['edge_fields'][edge_field_name] = {
                                    'type': type_name,
                                    'is_required': edge_field_name in self.db_schema['edge_collections'][edge_name].get('required', [])
                                }

            if domains and mutations:
                object_types.append(mutation)

            schema = self.template.render(
                domain=domain_data[domain_typename],
                mutations=mutations,
                graphql_types=list(GRAPHQL_TYPES.values()) + ['ID', 'DateTime'],
                default_limit=ARANGO_DEFAULT_LIMIT
            )
            self.schemas[domain_pathname] = make_executable_schema(schema, *object_types)

        log_perf.debug(f'Rebuild GraphQL engine schemas time: {(time.perf_counter() * 1000 - start):.2f} ms')
        logger.debug('Rebuilt GraphQL engine schemas')

    def check_invalid_recursive(self, db_attr):
        """Recursively check for object structures not representable in GraphQL"""
        result = False

        if db_attr.get('type') == 'object':
            properties = db_attr.get('properties')
        elif db_attr.get('type') == 'array' and db_attr.get('items', {}).get('type') == 'object':
            properties = db_attr.get('items', {}).get('properties')
        else:
            return False

        if not properties:
            return True

        for _, spec in properties.items():
            result = self.check_invalid_recursive(spec)

        return result

    def get_types_recursive(self, types, type_name, db_attr):
        """Recursively get subtypes (objects) for current domain substructure"""
        properties = {}

        if db_attr.get('type') == 'object':
            properties = db_attr.get('properties', {})

        elif db_attr.get('type') == 'array' and db_attr.get('items', {}).get('type') == 'object':
            properties = db_attr.get('items', {}).get('properties', {})

        for type_field_name, type_field_spec in properties.items():

            subtype_name = self.get_field_type(type_field_name, type_field_spec, type_field_spec)

            if subtype_name == pascalcase(type_field_name):
                types = self.get_types_recursive(types, type_field_name, type_field_spec)

            if type_name[0].islower():
                type_name = pascalcase(type_name)

            if type_name not in types:
                types[type_name] = {}

            types[type_name][type_field_name] = {
                'type': subtype_name
            }

        return types

    def get_constant_type(self, value):
        """Get GraphQL typename for constants"""
        if isinstance(value, str):
            return 'String'
        if isinstance(value, bool):
            return 'Boolean'
        if isinstance(value, float):
            return 'Float'
        if isinstance(value, int):
            return 'Int'

    def get_field_type(self, field_name, field_spec, db_attr):
        """Get GraphQL typename for resolved domain class field"""
        if field_spec in ('_id', '_key'):
            return 'ID'

        db_type = db_attr.get('type', 'string')

        if isinstance(db_type, list):
            db_type = db_type[0]

        if db_type == 'string' and db_attr.get('format') == 'date-time':
            return 'DateTime'

        if db_type in GRAPHQL_TYPES:
            return GRAPHQL_TYPES[db_type]

        if db_type == 'object':
            return pascalcase(field_name)

        if db_type == 'array':
            item_attr = db_attr.get('items', {})
            item_type = item_attr.get('type', 'string')

            if item_type == 'string' and item_attr.get('format') == 'date-time':
                return 'DateTime'

            if item_type in GRAPHQL_TYPES:
                return GRAPHQL_TYPES[item_type]

            if item_type == 'object':
                return pascalcase(field_name)

    def get_relation_type(self, field_name, relation_spec, class_name, domain_typename):
        """Get GraphQL typename for domain class relation"""
        edge_spec, edge_name, direction = relation_spec

        if isinstance(edge_spec, list):

            if len(edge_spec) > 1:
                return f'{pascalcase(class_name)}{pascalcase(field_name)}Union'

            if edge_spec[0] == 'ANY':
                return f'{domain_typename}Any'

            return pascalcase(edge_spec[0])

        if edge_spec == 'ANY':
            return f'{domain_typename}Any'

        return pascalcase(edge_spec)

    def get_field_resolver(self, field_name):
        """Generate a coroutine to resolve domain object fields"""
        async def field_resolver(obj, info, *args):
            return obj.get(field_name)
        return field_resolver

    def get_object_resolver(self, domain_spec, class_name, class_spec):
        """Generate a coroutine to look up backend object data, specifically or in bulk"""
        async def object_resolver(obj, info, **kwargs):

            start = time.perf_counter() * 1000

            request = info.context
            request.app.ctx.authorize(request, class_name, 'read', graphql=True)

            db = await get_arangodb()

            channel = f'pre_access_obj_{class_name}'
            listeners = await get_listeners(channel, request)

            ast = {}
            variables = {}

            if not obj and info.context:
                query = info.context.json.get('query')
                variables = info.context.json.get('variables', {})
                if query:
                    document = parse(query)
                    operations = separate_operations(document)
                    ast = defrag_ast(operations)
                    ast = get_ast_subtree(ast, info.field_name)

            if '_key' in kwargs:
                bind_vars = {'_id': f'{class_spec["resolver"]}/{kwargs["_key"]}'}

                fields = get_ast_fields(ast)
                relations = [rel for rel in fields if rel in class_spec.get('relations', {})]
                subqueries = get_subqueries(self.db_schema, domain_spec, class_spec, ast, relations, variables, bind_vars, ctx='GraphQL')
                return_ = get_return_spec(subqueries)

                query = prettify_aql(f'''
                WITH {get_all_collections(self.db_schema)}
                LET object = DOCUMENT(@_id)
                RETURN {return_}
                ''')
                results = db.aql(query, bind_vars=bind_vars)
                result = results['result']

                if result:
                    if listeners:
                        result, _ = await pre_rpc(channel, listeners, result, request)

                    result = add_constants(result[0], class_spec)
                    result = class_to_typename(result)

                log_perf.debug(f'GraphQL get object resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return result or None

            else:

                bind_vars = {}
                search_subset = self.app.ctx.search.get_search_subset(kwargs.get('search'), class_spec, bind_vars)
                attributes = class_spec.get('attributes', {})
                class_filters = get_class_filters([class_spec.get('class', class_name)])
                filters = get_filter_strings(kwargs.get('filter', []), attributes, bind_vars, ctx='GraphQL')
                sort = get_sort_string(kwargs.get('sort', []), attributes, ctx='GraphQL')
                skip = int(kwargs.get('skip', 0))
                limit = int(kwargs.get('limit', ARANGO_DEFAULT_LIMIT))

                fields = get_ast_fields(ast)
                relations = [rel for rel in fields if rel in class_spec.get('relations', {})]
                subqueries = get_subqueries(self.db_schema, domain_spec, class_spec, ast, relations, variables, bind_vars, ctx='GraphQL')
                return_ = get_return_spec(subqueries)

                query = prettify_aql(f'''
                WITH {get_all_collections(self.db_schema)}
                {search_subset}
                FOR object IN {class_spec["resolver"]}
                    {class_filters}
                    {filters}
                    {sort}
                    LIMIT {skip}, {limit}
                    RETURN {return_}
                ''')
                results = db.aql(query, bind_vars=bind_vars, total=True)
                total = results['total']
                results = results['result']

                if listeners:
                    results, _ = await pre_rpc(channel, listeners, results, request)

                for result in results:
                    result = add_constants(result, class_spec)
                    result = class_to_typename(result)

                log_perf.debug(f'GraphQL get object list resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return {'results_total': total, 'results': results}

        return object_resolver

    def get_edge_resolver(self, domain_spec, class_spec, relation):
        """Generate a coroutine to resolve domain object edges"""
        async def edge_resolver(obj, info, **kwargs):

            start = time.perf_counter() * 1000

            request = info.context

            edge_spec, edge_collection, depth_direction = class_spec['relations'][relation]

            ast = {}
            variables = {}

            if not obj and info.context:
                query = info.context.json.get('query')
                variables = info.context.json.get('variables', {})
                if query:
                    document = parse(query)
                    operations = separate_operations(document)
                    ast = defrag_ast(operations)
                    ast = get_ast_subtree(ast, info.field_name)

            if obj and obj.get(relation) is not None:
                results = obj.get(relation)
                total = len(results)  # TODO: get actual count

            else:
                request.app.ctx.authorize(request, obj.get('_class'), 'read', graphql=True)
                db = await get_arangodb()
                bind_vars = {
                    '_id': obj['_id'],
                    'edge_collection': edge_collection
                }
                edge_attributes = get_edge_attributes(self.db_schema, class_spec, relation)
                edge_filters = get_filter_strings(kwargs.get('edge_filter', []), edge_attributes, bind_vars, obj_name='edge', ctx='GraphQL')
                attributes = get_relation_attributes(domain_spec, class_spec, relation)
                type_filters = get_type_filters(domain_spec, edge_spec)
                search_filter = get_search_filter(kwargs.get('search'), bind_vars)
                filters = get_filter_strings(kwargs.get('filter', []), attributes, bind_vars, ctx='GraphQL')
                sort = get_sort_string(kwargs.get('sort', []), attributes, ctx='GraphQL')
                skip = int(kwargs.get('skip', 0))
                limit = int(kwargs.get('limit', ARANGO_DEFAULT_LIMIT))

                fields = get_ast_fields(ast)
                relations = [rel for rel in fields if rel in class_spec.get('relations', {})]
                subqueries = get_subqueries(self.db_schema, domain_spec, class_spec, ast, relations, variables, bind_vars, ctx='GraphQL')
                return_ = get_return_spec(subqueries, _edge=True)

                query = prettify_aql(f'''
                WITH {get_all_collections(self.db_schema)}
                LET doc = DOCUMENT(@_id)
                FOR object, object_edge IN {depth_direction} doc @edge_collection
                    {edge_filters}
                    {type_filters}
                    {search_filter}
                    {filters}
                    {sort}
                    LIMIT {skip}, {limit}
                    RETURN DISTINCT {return_}
                ''')
                results = db.aql(query, bind_vars=bind_vars, total=True)
                total = results['total']
                results = results['result']

            service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

            if isinstance(edge_spec, list):

                post_results = []
                results_by_class = {}

                for result in results:
                    _class = result.get('_class')

                    if _class not in results_by_class:
                        results_by_class[_class] = []

                    results_by_class[_class].append(result)

                for _class, class_results in results_by_class.items():
                    channel = f'pre_access_obj_{_class}'
                    listeners = service_rpcs.get(channel, [])

                    if listeners:
                        class_results, _ = await pre_rpc(channel, listeners, class_results, request)

                    post_results.extend(class_results)

                for result in post_results:
                    result = add_constants(result, class_spec)
                    result = class_to_typename(result)

                log_perf.debug(f'GraphQL get edge list resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return {'results_total': total, 'results': post_results}

            else:

                result = results[0]

                _class = result.get('_class')
                channel = f'pre_access_obj_{_class}'
                listeners = service_rpcs.get(channel, [])

                if listeners:
                    result, _ = await pre_rpc(channel, listeners, result, request)

                result = add_constants(result, class_spec)
                result = class_to_typename(result)

                log_perf.debug(f'GraphQL get edge resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return result or None

        return edge_resolver

    def get_mutation_resolver(self, class_name, class_spec, mutation_type, domain_pathname=None):
        """Generate a coroutine to resolve domain object data to backend object data,
           and create, update or delete them according to mutation type"""
        async def mutation_resolver(obj, info, **kwargs):

            start = time.perf_counter() * 1000

            db = await get_arangodb()
            request = info.context
            service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

            triggers = class_spec.get('triggers', [])
            trx_id = request.headers.get('x-arango-trx-id')
            input_ = kwargs.pop('input', {})
            _meta = input_.pop('_meta', {})
            data = translate_input(input_, class_spec)

            if '_key' in kwargs:
                data['_key'] = kwargs['_key']

            if mutation_type == 'create':

                request.app.ctx.authorize(request, class_name, 'create', graphql=True)

                data = set_defaults(data, class_spec['resolver'], self.db_schema)
                data['_class'] = class_spec.get('class', class_name)

                if 'set_creator' in triggers:
                    data = set_creator(data, request)

                if 'set_created' in triggers:
                    data = set_created(data)

                if 'set_updated' in triggers:
                    data = set_updated(data)

                if 'audit' in triggers and AUDIT_VERSIONING:
                    data['_version'] = None

                channel = f'pre_create_obj_{class_name}'
                listeners = service_rpcs.get(channel, [])

                if listeners:
                    data, trx_id = await pre_rpc(channel, listeners, data, request)
                    _meta = data.pop('_meta', _meta)

                _index = self.app.ctx.search.build_search_index(class_spec['resolver'], data)
                if _index:
                    data['_index'] = _index

                query = prettify_aql(f'''
                INSERT {json.dumps(data)}
                IN @@collection
                RETURN {{ new: NEW }}
                ''')
                bind_vars = {
                    '@collection': class_spec['resolver'],
                }
                result = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
                result = result['result'][0] if result['result'] else {}

                channel = f'post_create_obj_{class_name}'
                listeners = service_rpcs.get(channel, [])

                if listeners:
                    result['new']['_meta'] = _meta
                    coro = partial(post_rpc, channel, listeners, {}, result['new'], request)

                    if trx_id:
                        await coro()
                    else:
                        task = request.app.add_task(coro)
                        task.add_done_callback(task_handler)

                if 'audit' in triggers:
                    note = _meta.get('note')
                    coro = partial(audit, {}, result['new'], request, edge=False, note=note)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                result = class_to_typename(result['new'])

                log_perf.debug(f'GraphQL create object mutation resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return result or None

            if mutation_type == 'update':

                request.app.ctx.authorize(request, class_name, 'update', graphql=True)

                if 'set_updated' in triggers:
                    data = set_updated(data)

                channel = f'pre_update_obj_{class_name}'
                listeners = service_rpcs.get(channel, [])

                if listeners:
                    data, trx_id = await pre_rpc(channel, listeners, data, request)
                    _meta = data.pop('_meta', _meta)

                merge = 'true' if bool(kwargs.get('merge_objects', False)) else 'false'
                query = prettify_aql(f'''
                UPDATE {json.dumps(data)}
                IN @@collection
                OPTIONS {{ mergeObjects: {merge} }}
                RETURN {{ old: OLD, new: NEW }}
                ''')
                bind_vars = {
                    '@collection': class_spec['resolver'],
                }
                result = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
                result = result['result'][0] if result['result'] else {}

                channel = f'post_update_obj_{class_name}'
                listeners = service_rpcs.get(channel, [])

                if listeners:
                    result['new']['_meta'] = _meta
                    coro = partial(post_rpc, channel, listeners, result['old'], result['new'], request)

                    if trx_id:
                        await coro()
                    else:
                        task = request.app.add_task(coro)
                        task.add_done_callback(task_handler)

                if 'audit' in triggers:
                    note = _meta.get('note')
                    coro = partial(audit, result['old'], result['new'], request, edge=False, note=note)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                _index = self.app.ctx.search.build_search_index(class_spec['resolver'], result['new'])
                if _index:
                    update = {
                        '_key': result['new']['_key'],
                        '_index': _index,
                    }
                    query = prettify_aql(f'''
                    UPDATE {json.dumps(update)}
                    IN @@collection
                    ''')
                    db.aql(query, bind_vars=bind_vars, trx_id=trx_id)

                result = class_to_typename(result['new'])

                log_perf.debug(f'GraphQL update object mutation resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return result or None

            if mutation_type == 'delete':

                if NO_DELETE:
                    return False

                request.app.ctx.authorize(request, class_name, 'delete', graphql=True)

                query = prettify_aql('''
                REMOVE @_key IN @@collection
                RETURN { old: OLD }
                ''')
                bind_vars = {
                    '@collection': class_spec['resolver'],
                    '_key': kwargs['_key']
                }
                result = db.aql(query, bind_vars=bind_vars)
                result = result['result'][0] if result['result'] else {}

                channel = f'post_delete_obj_{class_name}'
                listeners = service_rpcs.get(channel, [])

                if listeners:
                    coro = partial(post_rpc, channel, listeners, result['old'], {}, request)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                if 'audit' in triggers:
                    coro = partial(audit, result['old'], {}, request, edge=False, note=None)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                log_perf.debug(f'GraphQL delete object mutation resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return bool(result)

        return mutation_resolver

    def get_edge_mutation_resolver(self, class_spec, mutation_type, edge_resolver,
        this_type=None, relation_spec=None, related_type=None, related_spec=None):
        """Generate a coroutine to resolve domain object data to backend object data,
           and create, update or delete them according to mutation type"""
        async def edge_mutation_resolver(obj, info, **kwargs):

            start = time.perf_counter() * 1000

            db = await get_arangodb()
            request = info.context
            trx_id = request.headers.get('x-arango-trx-id')
            triggers = class_spec.get('triggers', [])
            input_ = kwargs.pop('input', {})
            _meta = input_.pop('_meta', {})
            data = {}

            if mutation_type == 'create':

                request.app.ctx.authorize(request, snakecase(related_type), 'create', graphql=True)

                resolver = self.get_mutation_resolver(snakecase(related_type), related_spec, mutation_type)
                rel_result = await resolver({}, info, input=input_)

                if 'inbound' in kwargs.pop('direction', relation_spec[2] if relation_spec else ''):
                    from_resolver = self.type_resolver[related_type]
                    to_resolver = self.type_resolver[this_type]
                    from_key = rel_result.get('_key')
                    to_key = kwargs['_key']
                else:
                    from_resolver = self.type_resolver[this_type]
                    to_resolver = self.type_resolver[related_type]
                    from_key = kwargs['_key']
                    to_key = rel_result.get('_key')

                data['_from'] = f'{from_resolver}/{from_key}'
                data['_to'] = f'{to_resolver}/{to_key}'

                _edge = kwargs.pop('_edge', {})
                _edge = set_defaults(_edge, edge_resolver, self.db_schema)

                if 'set_creator' in triggers:
                    _edge = set_creator(_edge, request)

                if 'set_created' in triggers:
                    _edge = set_created(_edge)

                if 'set_updated' in triggers:
                    _edge = set_updated(_edge)

                data = {**data, **_edge}

                query = prettify_aql(f'''
                INSERT {json.dumps(data)}
                IN @@collection
                RETURN {{ new: NEW }}
                ''')
                bind_vars = {
                    '@collection': edge_resolver
                }
                result = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
                result = result['result'][0] if result['result'] else {}

                if 'audit' in triggers:
                    note = _meta.get('note')
                    coro = partial(audit, {}, result['new'], request, edge=True, note=note)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                log_perf.debug(f'GraphQL create edge mutation resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return {**rel_result, '_edge': result['new']}

            from_resolver = self.type_resolver[kwargs['from']['type']]
            to_resolver = self.type_resolver[kwargs['to']['type']]
            from_key = kwargs['from']['_key']
            to_key = kwargs['to']['_key']
            data['_from'] = f'{from_resolver}/{from_key}'
            data['_to'] = f'{to_resolver}/{to_key}'

            if mutation_type == 'attach':

                request.app.ctx.authorize(request, snakecase(kwargs['from']['type']), 'create', graphql=True)

                input_ = set_defaults(input_, edge_resolver, self.db_schema)

                if 'set_creator' in triggers:
                    input_ = set_creator(input_, request)

                if 'set_created' in triggers:
                    input_ = set_created(input_)

                if 'set_updated' in triggers:
                    input_ = set_updated(input_)

                data = {**data, **input_}

                query = prettify_aql(f'''
                INSERT {json.dumps(data)}
                IN @@collection
                RETURN {{ new: NEW }}
                ''')
                bind_vars = {
                    '@collection': edge_resolver
                }
                result = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
                result = result['result'][0] if result['result'] else {}

                if 'audit' in triggers:
                    note = _meta.get('note')
                    coro = partial(audit, {}, result['new'], request, edge=True, note=note)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                log_perf.debug(f'GraphQL attach edge mutation resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return bool(result)

            if mutation_type == 'update':

                request.app.ctx.authorize(request, snakecase(kwargs['from']['type']), 'update', graphql=True)

                if 'set_updated' in triggers:
                    input_ = set_updated(input_)

                merge = 'true' if bool(kwargs.get('merge_objects', False)) else 'false'
                query = prettify_aql(f'''
                FOR edge IN @@collection
                    FILTER edge._from == @_from && edge._to == @_to
                    UPDATE edge WITH {json.dumps(data)}
                    IN @@collection
                    OPTIONS {{ mergeObjects: {merge} }}
                    RETURN {{ old: OLD, new: NEW }}
                ''')
                bind_vars = {
                    '@collection': edge_resolver,
                    '_from': data['_from'],
                    '_to': data['_to']
                }
                results = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
                results = results['result']

                if not results:
                    return False

                for result in results:

                    if 'audit' in triggers:
                        note = _meta.get('note')
                        coro = partial(audit, result['old'], result['new'], request, edge=True, note=note)
                        task = request.app.add_task(coro)
                        task.add_done_callback(task_handler)

                log_perf.debug(f'GraphQL update edge mutation resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return bool(results)

            if mutation_type == 'detach':

                if NO_DELETE:
                    return False

                request.app.ctx.authorize(request, snakecase(kwargs['from']['type']), 'delete', graphql=True)

                query = prettify_aql('''
                FOR edge IN @@collection
                    FILTER edge._from == @_from && edge._to == @_to
                    REMOVE edge IN @@collection
                    RETURN { old: OLD }
                ''')
                bind_vars = {
                    '@collection': edge_resolver,
                    '_from': data['_from'],
                    '_to': data['_to']
                }
                results = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
                results = results['result']

                if not results:
                    return False

                for result in results:

                    if 'audit' in triggers:
                        coro = partial(audit, result['old'], {}, request, edge=True, note=None)
                        task = request.app.add_task(coro)
                        task.add_done_callback(task_handler)

                log_perf.debug(f'GraphQL detach edge mutation resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

                return bool(results)

        return edge_mutation_resolver

    async def graphql_graphiql(self, request, domain):
        """Serves an interactive environment for exploring the GraphQL API"""
        return response.html(self.graphiql_html)

    async def graphql_server(self, request, domain):
        """Handler for actual GraphQL requests"""
        schema = self.schemas.get(domain)
        if not schema:
            raise NotFound(f'No schema found for Domain {domain}', 404)

        data = request.json
        success, result = await graphql(
            schema=schema,
            data=data,
            logger='memoriam.error',
            context_value=request,
            root_value={},
            extensions=[
                AllFieldsExtension,
            ],
            debug=self.app.debug
        )

        result = AllFieldsExtension.post_process(result, domain, self.domain_cache)

        status_code = 200

        for error in result.get('errors', []):
            status_code = 400

            if error.get('message') == 'Unauthorized':
                status_code = 401

        return response.json(result, status_code)
