import re
import logging
import textwrap
import asyncio
from itertools import cycle

import httpx
import ujson as json

from caseconverter import snakecase
from graphql import GraphQLError
from graphql.utilities import ast_to_dict
from sanic.exceptions import SanicException, BadRequest

from memoriam.config import (
    AUTHLY_SERVICENAME,
    STORAGE_HOST, STORAGE_PORT, STORAGE_SCHEME,
    ARANGO_CONNECT_RETRIES, ARANGO_CONNECT_BACKOFF,
    ARANGO_DB_NAME, ARANGO_DEFAULT_LIMIT,
    REQUEST_TIMEOUT
)
from memoriam.constants import RESERVED_FIELDS


logger = logging.getLogger('memoriam')
log_aql = logging.getLogger('memoriam.aql')


class ArangoHTTPClient():
    """HTTP Client for ArangoDB using httpx"""

    def __init__(self, hosts=None, db_name=None, auth=None):
        self.hosts = hosts or [f'{STORAGE_SCHEME}://{STORAGE_HOST}:{STORAGE_PORT}']
        self.host = self._host_iter()
        self.db_name = db_name or ARANGO_DB_NAME
        self.headers = {
            'x-authly-entity-id': AUTHLY_SERVICENAME,
            'x-authly-entity-type': 'Service',
        }
        self.client = httpx.Client(auth=auth, http2=True, verify=False, timeout=REQUEST_TIMEOUT)

    def _host_iter(self):
        """Return an iterator that cycles through the hosts in self.hosts"""
        for host in cycle(self.hosts):
            yield host

    def _request(self, method, path, params=None, json=None, headers=None, raise_for_status=True):
        try:
            url = f'{next(self.host)}/{path}'
            headers = headers or self.headers
            response = self.client.request(method, url, params=params, json=json, headers=headers)
            if raise_for_status:
                response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            error_num = response.json().get('errorNum')
            error_msg = response.json().get('errorMessage')
            raise SanicException(f'Error on {e.request.method} {e.request.url}: [{error_num}] {error_msg}', e.response.status_code) from None
        except httpx.RequestError as e:
            raise SanicException(f'Error on {e.request.method} {e.request.url}')

    def ping(self):
        """Ping ArangoDB by checking the _system database"""
        url = '_db/_system/_api/collection'
        return self._request('get', url).json()

    def has_database(self, db_name):
        """Check if database exists"""
        url = '_db/_system/_api/database'
        return db_name in self._request('get', url).json()['result']

    def create_database(self, db_name):
        """Create a database"""
        data = {'name': db_name}
        url = '_db/_system/_api/database'
        return self._request('post', url, json=data).json()

    def has_collection(self, collection):
        """Check if collection exists"""
        url = f'_db/{self.db_name}/_api/collection'
        response = self._request('get', url).json()
        return collection in [c['name'] for c in response['result']]

    def create_collection(self, collection, edge=False):
        """Create a collection"""
        data = {'name': collection, 'type': 3 if edge else 2}
        url = f'_db/{self.db_name}/_api/collection'
        return self._request('post', url, json=data).json()

    def list_collections(self):
        """List collections"""
        url = f'_db/{self.db_name}/_api/collection'
        return self._request('get', url).json()

    def truncate_collection(self, collection):
        """Truncate a collection"""
        url = f'_db/{self.db_name}/_api/collection/{collection}/truncate'
        return self._request('put', url).json()

    def create_index(self, collection, data):
        """Create an index"""
        url = f'_db/{self.db_name}/_api/index?collection={collection}'
        return self._request('post', url, json=data).json()

    def list_indexes(self, collection):
        """List indexes"""
        url = f'_db/{self.db_name}/_api/index?collection={collection}'
        return self._request('get', url).json()

    def read_index(self, collection, id_):
        """Read an index"""
        url = f'_db/{self.db_name}/_api/index/{collection}/{id_}'
        return self._request('get', url).json()

    def delete_index(self, collection, id_):
        """Delete an index"""
        url = f'_db/{self.db_name}/_api/index/{collection}/{id_}'
        return self._request('delete', url).json()

    def create_view(self, data):
        """Create a view"""
        url = f'_db/{self.db_name}/_api/view'
        return self._request('post', url, json=data).json()

    def list_views(self):
        """List views"""
        url = f'_db/{self.db_name}/_api/view'
        return self._request('get', url).json()

    def read_view(self, name):
        """Read properties of a view"""
        url = f'_db/{self.db_name}/_api/view/{name}/properties'
        return self._request('get', url).json()

    def update_view(self, name, data):
        """Update a view"""
        url = f'_db/{self.db_name}/_api/view/{name}/properties'
        return self._request('patch', url, json=data).json()

    def delete_view(self, name):
        """Delete a view"""
        url = f'_db/{self.db_name}/_api/view/{name}'
        return self._request('delete', url).json()

    def create_analyzer(self, data):
        """Create an analyzer"""
        url = f'_db/{self.db_name}/_api/analyzer'
        return self._request('post', url, json=data).json()

    def list_analyzers(self):
        """List analyzers"""
        url = f'_db/{self.db_name}/_api/analyzer'
        return self._request('get', url).json()

    def read_analyzer(self, name):
        """Read definition of an analyzer"""
        url = f'_db/{self.db_name}/_api/analyzer/{name}'
        return self._request('get', url).json()

    def delete_analyzer(self, name):
        """Delete an analyzer"""
        url = f'_db/{self.db_name}/_api/analyzer/{name}'
        return self._request('delete', url).json()

    def aql(self, query, bind_vars=None, count=False, total=False, trx_id=None):
        """Execute an AQL query"""
        data = {
            'query': query,
            'bindVars': bind_vars or {},
            'count': count,
            'options': {
                'fullCount': total,
            }
        }

        headers = {**self.headers}
        if trx_id:
            headers['x-arango-trx-id'] = trx_id

        url = f'_db/{self.db_name}/_api/cursor'
        log_aql.debug(f'AQL query: {query}\nbind_vars: {bind_vars}\n')
        response = self._request('post', url, json=data, headers=headers)
        results = response.json()

        cid = results.get('id')
        count = results.get('count', 0)
        total = results.get('extra', {}).get('stats', {}).get('fullCount', 0)
        result = results.get('result', [])
        has_more = results.get('hasMore')

        if len(result) > 0 and not result[0]:
            result = []

        while has_more:
            url = f'_db/{self.db_name}/_api/cursor/{cid}'
            response = self._request('post', url)
            results = response.json()

            count += results.get('count', 0)
            result.extend(results.get('result', []))
            has_more = results.get('hasMore')

        return {
            'count': count or 0,
            'total': total or 0,
            'result': result,
        }

    def bulk_create(self, collection, data, sync=True, new=True, mode='conflict', trx_id=None):
        """Bulk create multiple documents"""
        params = {
            'waitForSync': sync,
            'returnNew': new,
            'overwriteMode': mode,
        }

        headers = {**self.headers}
        if trx_id:
            headers['x-arango-trx-id'] = trx_id

        url = f'_db/{self.db_name}/_api/document/{collection}'
        return self._request('post', url, params=params, json=data, headers=headers).json()

    def bulk_update(self, collection, data, sync=True, new=True, old=True, keep_null=True, merge=True, trx_id=None):
        """Bulk update multiple documents"""
        params = {
            'waitForSync': sync,
            'returnNew': new,
            'returnOld': old,
            'keepNull': keep_null,
            'mergeObjects': merge,
        }

        headers = {**self.headers}
        if trx_id:
            headers['x-arango-trx-id'] = trx_id

        url = f'_db/{self.db_name}/_api/document/{collection}'
        return self._request('patch', url, params=params, json=data, headers=headers).json()

    def bulk_delete(self, collection, data, sync=True, old=True, trx_id=None):
        """Bulk delete multiple documents"""
        params = {
            'waitForSync': sync,
            'returnOld': old,
        }

        headers = {**self.headers}
        if trx_id:
            headers['x-arango-trx-id'] = trx_id

        url = f'_db/{self.db_name}/_api/document/{collection}'
        return self._request('delete', url, params=params, json=data, headers=headers).json()


async def get_arangodb(hosts=None, db_name=None, auth=None):
    """Get a fresh ArangoDB database connection, defaults to backend database"""
    client = ArangoHTTPClient(hosts, db_name, auth)

    for retry in range(ARANGO_CONNECT_RETRIES):
        try:
            client.ping()
            break
        except Exception as e:
            if retry < (ARANGO_CONNECT_RETRIES - 1):
                await asyncio.sleep(ARANGO_CONNECT_BACKOFF)
            else:
                raise e from None

    return client


def get_all_collections(schema):
    """Get a comma-separated list of all collections in given schema for
       cluster-compatible WITH statements in AQL traversal queries"""
    collections = schema.get('collections', {}).keys()
    edge_collections = schema.get('edge_collections', {}).keys()
    return ', '.join(list(collections) + list(edge_collections))


def get_all_edge_collections(schema):
    """Get a comma-separated list of all edge collections in given schema"""
    edge_collections = schema.get('edge_collections', {}).keys()
    return ', '.join(list(edge_collections))


def prettify_aql(query):
    """Replace multiple newline chars to single, removing empty lines from templating"""
    query = textwrap.dedent(query)
    query = re.sub(r'\n+', r'\n', query)
    return query


def get_relation_attributes(domain_spec, class_spec, relation):
    """Resolve a dict of possible attributes for the given class_spec and relation"""
    edge_spec, _, _ = class_spec['relations'][relation]
    attributes = {}

    domain_spec_normalized = {snakecase(k): v for k, v in domain_spec.items()}

    if isinstance(edge_spec, list):
        if 'ANY' in edge_spec:
            for class_name, class_spec in domain_spec_normalized.items():
                attributes.update(class_spec.get('attributes', {}))
        else:
            for class_name in edge_spec:
                attributes.update(domain_spec_normalized.get(snakecase(class_name), {}).get('attributes', {}))
    else:
        if edge_spec == 'ANY':
            for class_name, class_spec in domain_spec_normalized.items():
                attributes.update(class_spec.get('attributes', {}))
        else:
            attributes = domain_spec_normalized.get(snakecase(edge_spec), {}).get('attributes', {})

    return attributes


def get_relation_relations(domain_spec, class_spec, relation):
    """Resolve a dict of possible relations for the given class_spec and relation"""
    edge_spec, _, _ = class_spec['relations'][relation]
    relations = {}

    domain_spec_normalized = {snakecase(k): v for k, v in domain_spec.items()}

    if isinstance(edge_spec, list):
        if 'ANY' in edge_spec:
            for class_name, class_spec in domain_spec_normalized.items():
                relations.update(class_spec.get('relations', {}))
        else:
            for class_name in edge_spec:
                relations.update(domain_spec_normalized.get(snakecase(class_name), {}).get('relations', {}))
    else:
        if edge_spec == 'ANY':
            for class_name, class_spec in domain_spec_normalized.items():
                relations.update(class_spec.get('relations', {}))
        else:
            relations = domain_spec_normalized.get(snakecase(edge_spec), {}).get('relations', {})

    return relations


def get_edge_attributes(db_schema, class_spec, relation):
    """Resolve a dict of edge attributes for the given class_spec and relation"""
    _, edge_collection, _ = class_spec['relations'][relation]
    attributes = {}

    for field in db_schema['edge_collections'][edge_collection].get('properties', {}):
        attributes[field] = field

    return attributes


def get_type_filters(domain_spec, edge_spec, obj_name='object'):
    """Get an AQL filter string for relation target class resolvers"""
    if not isinstance(edge_spec, list):
        edge_spec = [edge_spec]

    if 'ANY' in edge_spec:
        return ''

    terms = []
    domain_spec_normalized = {snakecase(k): v for k, v in domain_spec.items()}

    for target in edge_spec:
        class_spec = domain_spec_normalized.get(snakecase(target), {})
        resolver = class_spec.get('resolver')
        terms.append(f'IS_SAME_COLLECTION("{resolver}", {obj_name})')

    type_filter = 'FILTER '
    type_filter += ' OR '.join(terms)

    return type_filter


def get_class_filters(class_names, obj_name='object'):
    """Get an AQL filter string for target _classes"""
    terms = []
    for class_name in class_names:
        terms.append(f'{obj_name}._class == "{class_name}"')

    class_filter = 'FILTER '
    class_filter += ' OR '.join(terms)

    return class_filter


def get_filter_strings(filter_query, attributes, bind_vars, obj_name='object', ctx=None):
    """Get a set of AQL filter strings for the given Domain filter query.
       Will mutate bind_vars!"""
    filters = ''
    valid_ops = [
        '==','!=','<','<=','>','>=',
        'IN','NOTIN','LIKE','NOTLIKE',
        '=~','!~'
    ]

    if not filter_query:
        return filters

    if not isinstance(filter_query, list):
        filter_query = [filter_query]

    for statement in filter_query:

        try:
            key, op, val = statement.split(' ', 2)
        except ValueError:
            error = f'Invalid filter statement "{statement}"'
            logger.debug(error)
            if ctx and ctx == 'GraphQL':
                raise GraphQLError(error) from None
            else:
                raise BadRequest(error, status_code=400) from None

        field = attributes.get(key)

        if key in ['_key', '_class']:
            field = key

        if not field:
            error = f'Invalid filter statement: Field "{key}" is not part of domain object spec'
            logger.debug(error)
            if ctx and ctx == 'GraphQL':
                raise GraphQLError(error)
            else:
                raise BadRequest(error, status_code=400)

        if op not in valid_ops:
            error = f'Invalid filter operator "{op}"'
            logger.debug(error)
            if ctx and ctx == 'GraphQL':
                raise GraphQLError(error)
            else:
                raise BadRequest(error, status_code=400)

        if op == 'NOTIN':
            op = 'NOT IN'
        if op == 'NOTLIKE':
            op = 'NOT LIKE'

        try:
            val = val.replace("'", '"')
            val = json.loads(val)
        except json.JSONDecodeError:
            error = f'Invalid filter comparison value "{val}"'
            logger.debug(error)
            if ctx and ctx == 'GraphQL':
                raise GraphQLError(error)
            else:
                raise BadRequest(error, status_code=400)

        comp = f'{obj_name}_{field}_comp_{len(bind_vars) + 1}'
        filters += f'FILTER {obj_name}.{field} {op} @{comp}\n'
        bind_vars[comp] = val

        # TODO: support OR statements

    return filters


def get_parent_filters(parent_filter_query, relations, obj_name='object'):
    """Get a set of AQL filter strings for the given Domain filter query.
       Will mutate bind_vars!"""
    filters = ''

    for item in parent_filter_query:
        if item not in relations:
            error = f'Invalid parent_filter statement: {item} is not given in `relations`'
            raise BadRequest(error, status_code=400) from None

        filters += f'FILTER LENGTH({obj_name}_{item})\n'

    return filters


def get_search_filter(search_query, bind_vars, obj_name='object'):
    """Generate a search _filter_. NB: This is not the same as fulltext search, but a regular object filter based on token analysis."""

    if not search_query:
        return ''

    bind_vars['search'] = search_query

    return f'FILTER LENGTH(INTERSECTION(TOKENS({obj_name}._index, "text_en"), TOKENS(@search, "text_en"))) > 0'


def get_field_spec(fields_query, attributes, bind_vars, obj_name='object'):
    """Get an AQL return fields spec for the given Domain fields query.
       Will mutate bind_vars!"""
    fields = obj_name
    field_lines = []

    if not fields_query:
        return fields

    mod_fields = fields_query.copy()

    if not isinstance(mod_fields, list):
        mod_fields = [mod_fields]

    if '_class' not in mod_fields:
        mod_fields.insert(0, '_class')

    for key in mod_fields:
        field = attributes.get(key)

        if key in ['_key', '_class']:
            field = key

        if not field:
            error = f'Invalid field statement: Field "{key}" is not part of domain object spec'
            logger.debug(error)
            raise BadRequest(error, status_code=400)

        field_key = f'{obj_name}_{field}_key'
        field_lines.append(f'@{field_key}: {obj_name}.{field}')
        bind_vars[field_key] = key

    if field_lines:
        field_lines = ', '.join(field_lines)
        fields = textwrap.dedent(f'''{{
            {field_lines}
        }}''')

    # TODO: could be implemented simpler using KEEP
    return fields


def get_sort_string(sort_query, attributes, obj_name='object', ctx=None):
    """Get an AQL sort string for the given Domain sort query."""
    if not sort_query:
        return ''

    sorts = []
    for sort in sort_query:
        direction = ''

        if sort.startswith('-'):
            sort = sort[1:]
            direction = ' DESC'

        field = attributes.get(sort)

        if sort in ['_key', '_class']:
            field = sort

        if not field:
            error = f'Invalid sort statement: Field "{sort}" is not part of domain object spec'
            logger.debug(error)
            if ctx and ctx == 'GraphQL':
                raise GraphQLError(error)
            else:
                raise BadRequest(error, status_code=400)

        sorts.append(f'{obj_name}.{field}{direction}')

    if sorts and '_key' not in sort_query:
        sorts.append(f'{obj_name}._key')

    return 'SORT ' + ', '.join(sorts)


def defrag_ast(ast_operations):
    """Defragment an AST operation set, replacing fragment_spreads with fragment_definitions"""
    ast = {}
    fragments = {}

    def insert_fragments(ast, fragments):
        """Recursive function for replacing fragments with fragment definitions"""
        if ast.get('selection_set') is None:
            ast['selection_set'] = {}

        for i, selection in enumerate(ast.get('selection_set', {}).get('selections', [])):

            if selection.get('kind') == 'fragment_spread':
                name = selection.get('name', {}).get('value')
                fragment = fragments.get(name, {})
                fragment = insert_fragments(fragment, fragments)
                ast['selection_set']['selections'] = fragment['selection_set']['selections']

            elif selection.get('kind') == 'inline_fragment':
                fragment = insert_fragments(selection, fragments)
                ast['selection_set']['selections'] = fragment['selection_set']['selections']

            else:
                ast['selection_set']['selections'][i] = insert_fragments(selection, fragments)

        return ast

    for ast in ast_operations.values():
        ast_dict = ast_to_dict(ast)

        for definition in ast_dict.get('definitions', []):

            if definition.get('kind') == 'operation_definition':
                ast = definition

            if definition.get('kind') == 'fragment_definition':
                name = definition.get('name', {}).get('value')
                fragments[name] = definition

        ast = insert_fragments(ast, fragments)

    return ast


def get_ast_subtree(ast, field_name):
    """Search for and extract a subsection of a GraphQL AST dict using field name,
       replacing fragment spreads with fragment definitions."""
    if ast.get('selection_set') is None:
        ast['selection_set'] = {}

    subdict = {}
    for selection in ast.get('selection_set', {}).get('selections', []):

        if selection.get('name', {}).get('value') == field_name:
            return selection

        elif ast.get('selection_set'):
            subdict = get_ast_subtree(selection, field_name)

    return subdict


def get_ast_fields(ast):
    """Extract a set of fields from the top level of a GraphQL AST dict"""
    selections = ast.get('selection_set', {}).get('selections', [])

    for selection in selections:
        if selection.get('name', {}).get('value') == 'results':
            selections = selection.get('selection_set', {}).get('selections', [])
            break

    return [selection.get('name', {}).get('value') for selection in selections]


def cast_argument(argument):
    """Cast GraphQL AST argument to type using argument kind"""
    kind = argument.get('kind')
    value = argument.get('value')

    if kind == 'argument':
        kind = value.get('kind')

    if isinstance(value, dict):
        value = value.get('value')

    if kind == 'list_value':
        return [cast_argument(arg) for arg in argument.get('value').get('values', [])]

    if kind == 'string_value':
        return value

    if kind == 'int_value' and value is not None:
        return int(value)

    if kind == 'float_value' and value is not None:
        return float(value)

    if kind == 'boolean_value':
        return bool(value)


def get_ast_arguments(ast, variables):
    """Extract flattened dict of typecast arguments from a GraphQL AST dict"""
    arguments = {}
    for argument in ast.get('arguments', []):
        name = argument.get('name', {}).get('value')
        value = argument.get('value', {}).get('name', {}).get('value')

        if value in variables:
            arguments[name] = variables[value]
        else:
            arguments[name] = cast_argument(argument)

    return arguments


def get_return_spec(subqueries, obj_name='object', _edge=False):
    """Get an AQL MERGE return spec for the given set of subqueries"""
    if not subqueries and not _edge:
        return obj_name

    edge_line = f'{{_edge: UNSET({obj_name}_edge, "_id", "_key", "_rev", "_from", "_to")}},' if _edge else ''
    subqueries = ', '.join(subqueries)

    return f'''
    MERGE(
        {obj_name},
        {edge_line}
        {{
            {subqueries}
        }}
    )'''


def get_return_spec_v2(fields, relations, obj_name='object', _edge=False):
    """Get an AQL MERGE return spec for the given set of fields"""
    if fields == obj_name and not relations and not _edge:
        return obj_name

    edge_line = f'{{_edge: UNSET({obj_name}_edge, "_id", "_key", "_rev", "_from", "_to")}},' if _edge else ''
    subquery_spec = ', '.join(f'{relation}: {obj_name}_{relation}' for relation in relations)

    return f'''
    MERGE(
        {fields},
        {edge_line}
        {{
            {subquery_spec}
        }}
    )'''


def get_subqueries(db_schema, domain_spec, class_spec, ast, relations, variables, bind_vars, obj_name='object', ctx=None):
    """Extract subqueries for relations"""
    subobj_name = 'sub' + obj_name
    subqueries = []
    for relation in relations:
        relation_spec = class_spec.get('relations', {}).get(relation)
        if relation_spec:
            edge_spec, edge_collection, depth_direction = relation_spec

            subast = get_ast_subtree(ast, relation)
            kwargs = get_ast_arguments(subast, variables)

            edge_attributes = get_edge_attributes(db_schema, class_spec, relation)
            edge_filters = get_filter_strings(kwargs.get('edge_filter', []), edge_attributes, bind_vars, obj_name=f'{subobj_name}_edge', ctx=ctx)

            attributes = get_relation_attributes(domain_spec, class_spec, relation)
            type_filters = get_type_filters(domain_spec, edge_spec, obj_name=subobj_name)

            search_filter = get_search_filter(kwargs.get('search'), bind_vars, obj_name=subobj_name)
            filters = get_filter_strings(kwargs.get('filter', []), attributes, bind_vars, obj_name=subobj_name, ctx=ctx)

            sort = get_sort_string(kwargs.get('sort', []), attributes, obj_name=subobj_name, ctx=ctx)

            skip = int(kwargs.get('skip', 0))
            limit = int(kwargs.get('limit', ARANGO_DEFAULT_LIMIT))

            subclass_spec = {
                'attributes': 'attributes',
                'relations': get_relation_relations(domain_spec, class_spec, relation)
            }
            subfields = get_ast_fields(subast)
            subrelations = [rel for rel in subfields if rel in subclass_spec['relations']]
            subsubqueries = get_subqueries(db_schema, domain_spec, subclass_spec, subast, subrelations, variables, bind_vars, obj_name=subobj_name, ctx=ctx)
            return_ = get_return_spec(subsubqueries, obj_name=subobj_name, _edge=True)

            subquery = f'''
            {relation}: (
                FOR {subobj_name}, {subobj_name}_edge IN {depth_direction} {obj_name} {edge_collection}
                    {edge_filters}
                    {type_filters}
                    {search_filter}
                    {filters}
                    {sort}
                    LIMIT {skip}, {limit}
                    RETURN DISTINCT {return_}
            )
            '''
            subqueries.append(subquery)

    return subqueries


def get_dotted_queries(selection, subject=None, sublevel=0):
    """Extract terms from a `selection` according to a `subject` and `sublevel`"""
    result = []

    for item in selection:
        first_term, *rest = item.split(' ', 1)

        if sublevel == 0 and '.' not in first_term:
            result.append(item)

        else:
            parts = first_term.split('.', sublevel)
            if len(parts) > sublevel \
                and parts[sublevel - 1] == subject \
                and '.' not in parts[sublevel]:

                full_term = parts[sublevel] + ' ' + ' '.join(rest)
                result.append(full_term.strip())

    return result


def get_subqueries_v2(db_schema, domain_spec, class_spec, kwargs, relations, bind_vars, obj_name='object', ctx=None):
    """Extract subqueries for relations"""
    subobj_name = 'sub_' + obj_name
    sublevel = subobj_name.count('sub_')
    subqueries = []

    for relation in relations:
        relation_spec = class_spec.get('relations', {}).get(relation)
        if relation_spec:
            edge_spec, edge_collection, depth_direction = relation_spec

            edge_attributes = get_edge_attributes(db_schema, class_spec, relation)
            edge_filter_args = get_dotted_queries(kwargs.getlist('edge_filter', []), relation, sublevel)
            edge_filters = get_filter_strings(edge_filter_args, edge_attributes, bind_vars, obj_name=f'{subobj_name}_edge')

            attributes = get_relation_attributes(domain_spec, class_spec, relation)
            type_filters = get_type_filters(domain_spec, edge_spec, obj_name=subobj_name)

            subclass_spec = {
                'attributes': attributes,
                'relations': get_relation_relations(domain_spec, class_spec, relation)
            }

            subrelation_args = get_dotted_queries(kwargs.getlist('relation', []), relation, sublevel)
            subrelations = [rel for rel in subrelation_args if rel in subclass_spec['relations']]

            subsubqueries = get_subqueries_v2(db_schema, domain_spec, subclass_spec, kwargs, subrelations, bind_vars, obj_name=subobj_name)
            subsubquery_defs = ''.join(subsubqueries)

            subparent_filter_args = get_dotted_queries(kwargs.getlist('parent_filter', []), relation, sublevel)
            subparent_filters = get_parent_filters(subparent_filter_args, relations, obj_name=subobj_name)

            subfilter_args = get_dotted_queries(kwargs.getlist('filter', []), relation, sublevel)
            subfilters = get_filter_strings(subfilter_args, attributes, bind_vars, obj_name=subobj_name)

            subfield_args = get_dotted_queries(kwargs.getlist('field', []), relation, sublevel)
            subfields = get_field_spec(subfield_args, attributes, bind_vars, obj_name=subobj_name)

            subsort_args = get_dotted_queries(kwargs.getlist('sort', []), relation, sublevel)
            subsort = get_sort_string(subsort_args, attributes, obj_name=subobj_name)

            return_ = get_return_spec_v2(subfields, subrelations, obj_name=subobj_name)

            subquery = f'''
            LET {obj_name}_{relation} = (
                FOR {subobj_name}, {subobj_name}_edge IN {depth_direction} {obj_name} {edge_collection}
                    {edge_filters}
                    {type_filters}
                    {subsubquery_defs}
                    {subparent_filters}
                    {subfilters}
                    {subsort}
                    RETURN {return_}
            )
            '''
            subqueries.append(subquery)

    return subqueries


def get_diffs(pre, post):
    """Get diff objects for documents pre and post, with only the changes
       between pre and post (and vice versa), special fields excluded"""
    diff_skip_fields = [
        '_id',
        '_key',
        '_rev',
        '_class',
        '_index',
        '_meta',
        '_version',
        'creator',
        'created',
        'updated',
    ]

    pre_hashable = {}
    post_hashable = {}

    # convert lists to hashable tuples for set diff below
    for key, value in pre.items():
        pre_hashable[key] = json.dumps(value)

    for key, value in post.items():
        post_hashable[key] = json.dumps(value)

    pre_diff = {
        key: pre[key] for key, _ in pre_hashable.items() - post_hashable.items()
        if key not in diff_skip_fields
    }
    post_diff = {
        key: post[key] for key, _ in post_hashable.items() - pre_hashable.items()
        if key not in diff_skip_fields
    }

    return pre_diff, post_diff


def set_defaults(data, resolver, db_schema):
    """Set field defaults as specified in db schema"""
    collections = {**db_schema.get('collections', {}), **db_schema.get('edge_collections', {})}
    for field_name, field_spec in collections[resolver]['properties'].items():

        default = field_spec.get('default')
        if default is not None and field_name not in data:
            data[field_name] = default

    return data


def translate_input(input_, klass):
    """Translate domain data input to backend database input"""
    data = {}

    for domain_field_name, field_name in klass.get('attributes', {}).items():
        if input_ and domain_field_name in input_:
            data[field_name] = input_[domain_field_name]

    if klass.get('permissive') in ('input', 'both'):
        for field_name in input_:
            if (field_name not in RESERVED_FIELDS and
                field_name not in data and
                field_name not in klass.get('attributes', {})):
                data[field_name] = input_[field_name]

    return data


def translate_output(output, klass, db_schema=None, relations=[]):
    """Translate backend database output to domain data output"""
    data = {}

    if _key := output.get('_key'):
        data['_key'] = _key
    if _class := output.get('_class'):
        data['_class'] = _class

    for field, value in klass.get('constants', {}).items():
        data[field] = value

    for domain_field_name, field_name in klass.get('attributes', {}).items():
        if output and field_name in output:

            if db_schema:
                db_attr = db_schema['collections'][klass['resolver']]['properties'].get(field_name, {})
                if db_attr.get('writeOnly'):
                    continue

            data[domain_field_name] = output[field_name]

    if klass.get('permissive') in ('output', 'both'):
        for field_name in output:

            if db_schema:
                db_attr = db_schema['collections'][klass['resolver']]['properties'].get(field_name, {})
                if db_attr.get('writeOnly'):
                    continue

            if (field_name not in RESERVED_FIELDS and
                field_name not in data and
                field_name not in klass.get('attributes', {}).values()):
                data[field_name] = output[field_name]

            if field_name == '_edge':
                data['_edge'] = output['_edge']

    for relation in relations:
        if relation in output:
            data[relation] = output[relation]

    return data


def translate_relations(results, db_schema, domain_spec, kwargs, relations, level=0):
    for result in results:
        for relation in relations:
            relation_results = result.get(relation, [])

            # TODO: make a note and reverse
            if not isinstance(relation_results, list):
                relation_results = [relation_results]

            if relation_results:
                _class = relation_results[0].get('_class', '')

                subclass_spec = domain_spec.get(_class, {})
                subrelations = get_dotted_queries(kwargs.getlist('relation', []), relation, level + 1)
                subfields = get_dotted_queries(kwargs.getlist('field', []), relation, level + 1)

                if not subfields:
                    relation_results = [translate_output(subresult, subclass_spec, db_schema, subrelations) for subresult in relation_results]
                elif '_class' not in subfields:
                    for r in relation_results:
                        del r['_class']

                if subrelations:
                    relation_results = translate_relations(relation_results, db_schema, domain_spec, kwargs, subrelations, level + 1)

                result[relation] = relation_results

    return results


def add_constants(obj, class_spec):
    """Add constant values from class_spec, if any"""
    for key, value in class_spec.get('constants', {}).items():
        obj[key] = value

    return obj
