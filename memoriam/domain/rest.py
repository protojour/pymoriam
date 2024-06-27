import os
import time
import logging

from functools import partial

import ujson as json
from caseconverter import snakecase
from sanic import response
from sanic.exceptions import SanicException, InvalidUsage, NotFound

from memoriam.config import (
    ARANGO_DOMAIN_DB_NAME, ARANGO_SCHEMA_PATH, ARANGO_DEFAULT_LIMIT,
    NO_DELETE, AUDIT_LOG_DB, AUDIT_VERSIONING, RELOAD_SCHEMAS
)
from memoriam.arangodb import (
    get_arangodb, prettify_aql, get_edge_attributes, get_relation_attributes,
    get_type_filters, get_class_filters, get_filter_strings, get_sort_string, get_field_spec,
    get_dotted_queries, get_parent_filters, get_subqueries_v2, get_return_spec_v2,
    get_all_collections, get_all_edge_collections, set_defaults,
    translate_input, translate_output, translate_relations, get_search_filter
)
from memoriam.constants import OPERATIONS, RESERVED_FIELDS
from memoriam.openapi import OpenAPI
from memoriam.domain.domain import parse_all_relations
from memoriam.domain.jinja import env as jinja_env
from memoriam.domain.rpc import pre_rpc, post_rpc, get_listeners
from memoriam.domain.triggers import set_creator, set_created, set_updated, audit
from memoriam.utils import load_yaml, task_handler


logging.getLogger('asyncio').setLevel(logging.ERROR)
logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')


class RESTResolverEngine:
    """This Sanic extension transforms domain schemas to working REST APIs,
       and handles translation between domain data formats and backend data formats"""

    def __init__(self, app):
        self.app = app
        self.app.ctx.rest_engine = self
        self.openapi = OpenAPI(
            app=self.app,
            base_url='/<namespace>/api'
        )
        self.db_schema = load_yaml(path=ARANGO_SCHEMA_PATH)
        self.template = jinja_env.get_template('openapi_spec_domain.yml')
        self.domain_cache = {}

        app.register_listener(self.rebuild_schema, 'before_server_start')

        if RELOAD_SCHEMAS:
            app.register_middleware(self.schema_middleware, 'request')

        app.add_route(
            handler=self.domain_search_resolver,
            uri='/<domain>/api/search',
            methods=['GET']
        )
        app.add_route(
            handler=self.domain_obj_list_resolver,
            uri='/<domain>/api/<domain_class>',
            methods=['GET']
        )
        app.add_route(
            handler=self.domain_obj_post_resolver,
            uri='/<domain>/api/<domain_class>',
            methods=['POST']
        )
        app.add_route(
            handler=self.domain_bulk_obj_post_resolver,
            uri='/<domain>/api/<domain_class>/_bulk',
            methods=['POST']
        )
        app.add_route(
            handler=self.domain_bulk_obj_patch_resolver,
            uri='/<domain>/api/<domain_class>/_bulk',
            methods=['PATCH']
        )
        app.add_route(
            handler=self.domain_bulk_obj_delete_resolver,
            uri='/<domain>/api/<domain_class>/_bulk',
            methods=['DELETE']
        )
        app.add_route(
            handler=self.domain_obj_get_resolver,
            uri='/<domain>/api/<domain_class>/<_key>',
            methods=['GET']
        )
        app.add_route(
            handler=self.domain_obj_patch_resolver,
            uri='/<domain>/api/<domain_class>/<_key>',
            methods=['PATCH']
        )
        app.add_route(
            handler=self.domain_obj_delete_resolver,
            uri='/<domain>/api/<domain_class>/<_key>',
            methods=['DELETE']
        )
        app.add_route(
            handler=self.relation_list_resolver,
            uri='/<domain>/api/<domain_class>/<_key>/<relation>',
            methods=['GET']
        )
        app.add_route(
            handler=self.relation_post_resolver,
            uri='/<domain>/api/<domain_class>/<_key>/<relation>',
            methods=['POST']
        )
        app.add_route(
            handler=self.relation_patch_resolver,
            uri='/<domain>/api/<domain_class>/<_key>/<relation>',
            methods=['PATCH']
        )
        app.add_route(
            handler=self.relation_delete_resolver,
            uri='/<domain>/api/<domain_class>/<_key>/<relation>',
            methods=['DELETE']
        )
        app.add_route(
            handler=self.neighbors_resolver,
            uri='/<domain>/api/<domain_class>/<_key>/_neighbors',
            methods=['GET']
        )
        if AUDIT_LOG_DB:
            app.add_route(
                handler=self.changes_resolver,
                uri='/<domain>/api/<domain_class>/<_key>/_changes',
                methods=['GET']
            )

    async def schema_middleware(self, request):
        """Middleware to trigger a schema rebuild if necessary"""
        pid = os.getpid()
        built = await self.app.ctx.redis.sismember('memoriam_rest_schemas', pid)
        if not built:
            await self.rebuild_schema(self.app)

    async def rebuild_schema(self, app):
        """Rebuild REST spec from currently stored domain schemas"""
        pid = os.getpid()
        await app.ctx.redis.sadd('memoriam_rest_schemas', pid)

        start = time.perf_counter() * 1000
        logger.debug('Rebuilding REST engine cache...')

        db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)
        service_info = await app.ctx.cache.get('service_info', {})

        query = prettify_aql('''
        FOR object IN domain
            FILTER object.active == true
            RETURN object
        ''')
        result = db.aql(query)
        domains = result['result']

        for domain in domains:

            domain.pop('_resources', None)

            label = snakecase(domain['label'])
            schema = load_yaml(domain['schema'])
            schema = {snakecase(k): v for k, v in schema.items()}
            indexed_classes = []

            for class_name, class_spec in schema.items():

                # set default for class if not set
                if 'class' not in class_spec:
                    schema[class_name]['class'] = class_name

                # set default for operations if not set
                if 'operations' not in class_spec:
                    schema[class_name]['operations'] = OPERATIONS

                # set default for permissive if not set
                if 'permissive' not in class_spec:
                    schema[class_name]['permissive'] = 'no'

                # search indexed and readable, add to indexed_classes (to be used in spec)
                if (class_spec['resolver'] in self.app.ctx.search.view_props.get('links', {}) and
                    'read' in schema[class_name]['operations']):
                    indexed_classes.append(class_name)

                # if this is an alias class, merge operations on the root class
                alias = snakecase(class_spec.get('alias', class_name))
                if alias != class_name:
                    schema[class_name]['class'] = alias
                    schema[alias]['operations'] = list(set([
                        *schema[alias]['operations'],
                        *class_spec['operations']
                    ]))

                # set (alias) class to be used for each operation
                for operation in class_spec['operations']:
                    schema[alias][f'{operation}_class'] = class_name

            for service_name, service_spec in service_info.items():

                service_rpcs = service_spec.get('rpc', {})
                for class_name, class_spec in service_rpcs.items():
                    if class_name in schema:

                        if 'listeners' not in schema[class_name]:
                            schema[class_name]['listeners'] = []

                        schema[class_name]['listeners'].append({
                            **class_spec,
                            'name': service_name,
                            'host': service_spec.get('host')
                        })

            self.domain_cache[label] = schema

            yaml_spec = self.template.render(
                db_schema=self.db_schema,
                domain=domain,
                schema=schema,
                default_limit=ARANGO_DEFAULT_LIMIT,
                indexed_classes=indexed_classes,
                reserved_fields=RESERVED_FIELDS,
                include_changes_api=AUDIT_LOG_DB
            )
            dict_spec = load_yaml(yaml_spec)

            self.openapi.init_spec(namespace=label, spec=dict_spec)

        await app.ctx.cache.set('domain_cache', self.domain_cache)

        log_perf.debug(f'Rebuild REST engine cache time: {(time.perf_counter() * 1000 - start):.2f} ms')
        logger.debug('Rebuilt REST engine cache')

        return self.domain_cache

    async def domain_search_resolver(self, request, domain):
        """Handler for domain-specific search"""

        start = time.perf_counter() * 1000

        db = await get_arangodb()
        service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = {
            'resolver': 'search',
            'relations': {
                'search': ['ANY', None, None]
            }
        }

        bind_vars = {}
        search_subset = self.app.ctx.search.get_search_subset(request.args.get('search'), class_spec, bind_vars, all_=True)
        attributes = get_relation_attributes(domain_spec, class_spec, 'search')
        classes = [klass['class'] for klass in domain_spec.values()]
        class_filters = get_class_filters(classes)
        filters = get_filter_strings(request.args.getlist('filter', []), attributes, bind_vars)
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', ARANGO_DEFAULT_LIMIT))

        query = prettify_aql(f'''
        WITH {get_all_collections(self.db_schema)}
        {search_subset}
        FOR object IN search
            {class_filters}
            {filters}
            SORT TFIDF(object) DESC
            LIMIT {skip}, {limit}
            RETURN object
        ''')
        results = db.aql(query, bind_vars=bind_vars, total=True)
        total = results['total']
        results = results['result']

        results_by_class = {}
        for result in results:
            _class = result.get('_class')

            if _class not in results_by_class:
                results_by_class[_class] = []

            results_by_class[_class].append(result)

        post_results = []
        for _class, results in results_by_class.items():
            channel = f'pre_access_obj_{_class}'
            listeners = service_rpcs.get(channel, [])

            if listeners:
                rpc_results, _ = await pre_rpc(channel, listeners, results, request)
                post_results.extend(rpc_results)
            else:
                post_results.extend(results)

        results = [
            translate_output(result, self.domain_cache[domain][result.get('_class')], self.db_schema)
            for result in post_results
        ]
        results_obj = {
            'skip': skip,
            'limit': limit,
            'results_total': total,
            'results': results
        }

        log_perf.debug(f'REST search resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(results_obj, 200)

    async def domain_obj_list_resolver(self, request, domain, domain_class):
        """Handler for domain object listings"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'read')

        db = await get_arangodb()

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('read_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'read' not in operations:
            raise SanicException("Operation 'read' is not permitted for this domain class", 405)

        bind_vars = {}
        search_subset = self.app.ctx.search.get_search_subset(request.args.get('search'), class_spec, bind_vars)
        attributes = class_spec.get('attributes', {})
        class_filters = get_class_filters([class_spec.get('class', domain_class)])

        relation_args = get_dotted_queries(request.args.getlist('relation', []))
        relations = [rel for rel in relation_args if rel in class_spec.get('relations', {})]

        subqueries = get_subqueries_v2(self.db_schema, domain_spec, class_spec, request.args, relations, bind_vars)
        subquery_defs = ''.join(subqueries)

        parent_filter_args = get_dotted_queries(request.args.getlist('parent_filter', []))
        parent_filters = get_parent_filters(parent_filter_args, relations)

        filter_args = get_dotted_queries(request.args.getlist('filter', []))
        filters = get_filter_strings(filter_args, attributes, bind_vars)

        field_args = get_dotted_queries(request.args.getlist('field', []))
        fields = get_field_spec(field_args, attributes, bind_vars)

        sort_args = get_dotted_queries(request.args.getlist('sort', []))
        sort = get_sort_string(sort_args, attributes)

        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', ARANGO_DEFAULT_LIMIT))
        return_ = get_return_spec_v2(fields, relations)

        query = prettify_aql(f'''
        WITH {get_all_collections(self.db_schema)}
        {search_subset}
        FOR object IN {class_spec["resolver"]}
            {class_filters}
            {subquery_defs}
            {parent_filters}
            {filters}
            {sort}
            LIMIT {skip}, {limit}
            RETURN {return_}
        ''')
        results = db.aql(query, bind_vars=bind_vars, total=True)
        total = results['total']
        results = results['result']

        channel = f'pre_access_obj_{domain_class}'
        listeners = await get_listeners(channel, request)

        if listeners:
            results, _ = await pre_rpc(channel, listeners, results, request)

        if fields == 'object':
            results = [translate_output(result, class_spec, self.db_schema, relations) for result in results]
        elif '_class' not in request.args.getlist('field', []):
            for result in results:
                del result['_class']

        if relations:
            results = translate_relations(results, self.db_schema, domain_spec, request.args, relations)

        results_obj = {
            'skip': skip,
            'limit': limit,
            'results_total': total,
            'results': results
        }

        log_perf.debug(f'REST object list resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(results_obj, 200)

    async def domain_obj_post_resolver(self, request, domain, domain_class):
        """Handler for domain object creation"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'create')

        db = await get_arangodb()
        service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('create_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'create' not in operations:
            raise SanicException("Operation 'create' is not permitted for this domain class", 405)

        data = request.json
        _meta = data.pop('_meta', {})
        trx_id = request.headers.get('x-arango-trx-id')
        triggers = class_spec.get('triggers', [])

        data = translate_input(data, class_spec)
        data = set_defaults(data, class_spec['resolver'], self.db_schema)
        data['_class'] = class_spec.get('class', domain_class)

        if 'set_creator' in triggers:
            data = set_creator(data, request)

        if 'set_created' in triggers:
            data = set_created(data)

        if 'set_updated' in triggers:
            data = set_updated(data)

        if 'audit' in triggers and AUDIT_VERSIONING:
            data['_version'] = None

        channel = f'pre_create_obj_{domain_class}'
        listeners = service_rpcs.get(channel, [])

        if listeners:
            data['_meta'] = _meta
            data, trx_id = await pre_rpc(channel, listeners, data, request)
            request.headers['x-arango-trx-id'] = trx_id
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

        channel = f'post_create_obj_{domain_class}'
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

        result = translate_output(result['new'], class_spec, self.db_schema)

        log_perf.debug(f'REST object post resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(result, 201)

    async def domain_bulk_obj_post_resolver(self, request, domain, domain_class):
        """Handler for bulk domain object creation"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'create')

        db = await get_arangodb()
        service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('create_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'create' not in operations:
            raise SanicException("Operation 'create' is not permitted for this domain class", 405)

        data = request.json
        trx_id = request.headers.get('x-arango-trx-id')
        triggers = class_spec.get('triggers', [])

        meta = [item.pop('_meta', {}) for item in data]
        data = [translate_input(item, class_spec) for item in data]
        data = [set_defaults(item, class_spec['resolver'], self.db_schema) for item in data]

        channel = f'pre_create_obj_{domain_class}'
        listeners = service_rpcs.get(channel, [])

        for item, _meta in zip(data, meta):
            item['_class'] = class_spec.get('class', domain_class)

            if 'set_creator' in triggers:
                item = set_creator(item, request)

            if 'set_created' in triggers:
                item = set_created(item)

            if 'set_updated' in triggers:
                item = set_updated(item)

            item['_meta'] = _meta
            item, trx_id = await pre_rpc(channel, listeners, item, request)
            request.headers['x-arango-trx-id'] = trx_id

            _index = self.app.ctx.search.build_search_index(class_spec['resolver'], item)
            if _index:
                item['_index'] = _index

        for item in data:
            if '_meta' in item:
                del item['_meta']

        sync = request.args.get('sync', True)
        new = request.args.get('new', True)
        mode = request.args.get('mode', 'conflict')

        results = db.bulk_create(class_spec['resolver'], data, sync, new, mode, trx_id)

        channel = f'post_create_obj_{domain_class}'
        listeners = service_rpcs.get(channel, [])

        for result, _meta in zip(results, meta):
            item = result

            if 'new' in result:
                item = result['new']

                if listeners:
                    item['_meta'] = _meta
                    coro = partial(post_rpc, channel, listeners, {}, item, request)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                    if '_meta' in item:
                        del item['_meta']

                if 'audit' in triggers:
                    note = _meta.get('note')
                    coro = partial(audit, {}, item, request, edge=False, note=note)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

            result = translate_output(item, class_spec, self.db_schema)

        log_perf.debug(f'REST object post resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(results, 201)

    async def domain_bulk_obj_patch_resolver(self, request, domain, domain_class):
        """Handler for bulk domain object update"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'update')

        db = await get_arangodb()
        service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('update_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'update' not in operations:
            raise SanicException("Operation 'update' is not permitted for this domain class", 405)

        data = request.json
        trx_id = request.headers.get('x-arango-trx-id')
        triggers = class_spec.get('triggers', [])

        keys = [item.get('_key') for item in data]
        meta = [item.pop('_meta', {}) for item in data]
        data = [translate_input(item, class_spec) for item in data]

        channel = f'pre_update_obj_{domain_class}'
        listeners = service_rpcs.get(channel, [])

        for item, _key, _meta in zip(data, keys, meta):
            if 'set_updated' in triggers:
                item = set_updated(item)

            item['_key'] = _key
            item['_meta'] = _meta
            item, trx_id = await pre_rpc(channel, listeners, item, request)
            request.headers['x-arango-trx-id'] = trx_id

        for item in data:
            if '_meta' in item:
                del item['_meta']

        sync = request.args.get('sync', True)
        new = request.args.get('new', False if not sync else True)
        old = request.args.get('old', False if not sync else True)
        keep_null = request.args.get('keep_null', True)
        merge = request.args.get('merge', False)

        results = db.bulk_update(class_spec['resolver'], data, sync, new, old, keep_null, merge, trx_id)

        channel = f'post_update_obj_{domain_class}'
        listeners = service_rpcs.get(channel, [])

        for result, _meta in zip(results, meta):
            item = result

            if 'old' in result and 'new' in result:
                if listeners:
                    item['_meta'] = _meta
                    coro = partial(post_rpc, channel, listeners, result['old'], result['new'], request)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                if 'audit' in triggers:
                    note = _meta.get('note')
                    coro = partial(audit, result['old'], result['new'], request, edge=False, note=note)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

            if 'new' in result:
                item = result['new']

                if sync:
                    _index = self.app.ctx.search.build_search_index(class_spec['resolver'], result['new'])
                    if _index:
                        results = db.bulk_update(class_spec['resolver'], data, sync, new, old, keep_null, merge)

            result = translate_output(item, class_spec, self.db_schema)

        log_perf.debug(f'REST object patch resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(results, 200)

    async def domain_bulk_obj_delete_resolver(self, request, domain, domain_class):
        """Handler for bulk domain object deletion"""

        if NO_DELETE:
            raise SanicException('Object deletions are disabled', 405)

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'delete')

        db = await get_arangodb()

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('delete_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'delete' not in operations:
            raise SanicException("Operation 'delete' is not permitted for this domain class", 405)

        data = request.json
        trx_id = request.headers.get('x-arango-trx-id')
        triggers = class_spec.get('triggers', [])

        sync = request.args.get('sync', True)
        old = request.args.get('old', True)

        results = db.bulk_delete(class_spec['resolver'], data, sync, old, trx_id)

        channel = f'post_delete_obj_{domain_class}'
        listeners = await get_listeners(channel, request)

        for result in results:
            item = result

            if 'old' in result:
                item = result['old']

                if listeners:
                    coro = partial(post_rpc, channel, listeners, result['old'], {}, request)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

                if 'audit' in triggers:
                    coro = partial(audit, result['old'], {}, request)
                    task = request.app.add_task(coro)
                    task.add_done_callback(task_handler)

            result = translate_output(item, class_spec, self.db_schema)

        log_perf.debug(f'REST object delete resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(results, 200)

    async def domain_obj_get_resolver(self, request, domain, domain_class, _key):
        """Handler for domain object access"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'read')

        db = await get_arangodb()

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('read_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'read' not in operations:
            raise SanicException("Operation 'read' is not permitted for this domain class", 405)

        attributes = class_spec.get('attributes', {})
        bind_vars = {'_id': f'{class_spec["resolver"]}/{_key}'}

        relation_args = get_dotted_queries(request.args.getlist('relation', []))
        relations = [rel for rel in relation_args if rel in class_spec.get('relations', {})]

        subqueries = get_subqueries_v2(self.db_schema, domain_spec, class_spec, request.args, relations, bind_vars)
        subquery_defs = ','.join(subqueries)

        field_args = get_dotted_queries(request.args.getlist('field', []))
        fields = get_field_spec(field_args, attributes, bind_vars)

        return_ = get_return_spec_v2(fields, relations)

        query = prettify_aql(f'''
        LET object = DOCUMENT(@_id)
        {subquery_defs}
        RETURN {return_}
        ''')
        results = db.aql(query, bind_vars=bind_vars)
        result = results['result']

        if not result:
            raise NotFound(f'{domain_class} {_key} does not exist', 404)

        channel = f'pre_access_obj_{domain_class}'
        listeners = await get_listeners(channel, request)

        if listeners:
            result, _ = await pre_rpc(channel, listeners, result, request)

        result = result[0]

        if fields == 'object':
            result = translate_output(result, class_spec, self.db_schema, relations)
        elif '_class' not in request.args.getlist('field', []):
            del result['_class']

        if relations:
            result = translate_relations([result], self.db_schema, domain_spec, request.args, relations)
            result = result[0]

        log_perf.debug(f'REST object get resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(result, 200)

    async def domain_obj_patch_resolver(self, request, domain, domain_class, _key):
        """Handler for domain object update"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'update')

        db = await get_arangodb()
        service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('update_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'update' not in operations:
            raise SanicException("Operation 'update' is not permitted for this domain class", 405)

        triggers = class_spec.get('triggers', [])

        data = request.json
        _meta = data.pop('_meta', {})
        trx_id = request.headers.get('x-arango-trx-id')

        data = translate_input(data, class_spec)
        data['_key'] = _key

        if 'set_updated' in triggers:
            data = set_updated(data)

        channel = f'pre_update_obj_{domain_class}'
        listeners = service_rpcs.get(channel, [])

        if listeners:
            data['_meta'] = _meta
            data, trx_id = await pre_rpc(channel, listeners, data, request)
            request.headers['x-arango-trx-id'] = trx_id
            _meta = data.pop('_meta', _meta)

        merge = 'true' if bool(request.args.get('merge_objects', False)) else 'false'
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

        channel = f'post_update_obj_{domain_class}'
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
            db.aql(query, bind_vars=bind_vars)

        result = translate_output(result['new'], class_spec, self.db_schema)

        log_perf.debug(f'REST object patch resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(result, 200)

    async def domain_obj_delete_resolver(self, request, domain, domain_class, _key):
        """Handler for domain object deletion"""

        if NO_DELETE:
            raise SanicException('Object deletions are disabled', 405)

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'delete')

        db = await get_arangodb()

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('delete_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'delete' not in operations:
            raise SanicException("Operation 'delete' is not permitted for this domain class", 405)

        trx_id = request.headers.get('x-arango-trx-id')
        triggers = class_spec.get('triggers', [])

        query = prettify_aql('''
        REMOVE @_key IN @@collection
        RETURN { old: OLD }
        ''')
        bind_vars = {
            '@collection': class_spec['resolver'],
            '_key': _key
        }
        result = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
        result = result['result'][0] if result['result'] else {}

        channel = f'post_delete_obj_{domain_class}'
        listeners = await get_listeners(channel, request)

        if listeners:
            coro = partial(post_rpc, channel, listeners, result['old'], {}, request)
            task = request.app.add_task(coro)
            task.add_done_callback(task_handler)

        if 'audit' in triggers:
            coro = partial(audit, result['old'], {}, request, edge=False, note=None)
            task = request.app.add_task(coro)
            task.add_done_callback(task_handler)

        log_perf.debug(f'REST object delete resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.empty()

    async def relation_list_resolver(self, request, domain, domain_class, _key, relation):
        """Handler for domain object relation listings"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'read')

        db = await get_arangodb()

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('read_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        edge_spec, edge_collection, depth_direction = class_spec['relations'][relation]

        bind_vars = {
            '_id': f'{class_spec["resolver"]}/{_key}',
            'edge_collection': edge_collection
        }
        edge_attributes = get_edge_attributes(self.db_schema, class_spec, relation)
        edge_filters = get_filter_strings(request.args.getlist('edge_filter', []), edge_attributes, bind_vars, obj_name='edge')
        attributes = get_relation_attributes(domain_spec, class_spec, relation)
        type_filters = get_type_filters(domain_spec, edge_spec)
        search_filter = get_search_filter(request.args.get('search'), bind_vars)
        filters = get_filter_strings(request.args.getlist('filter', []), attributes, bind_vars)
        fields = get_field_spec(request.args.getlist('field', []), attributes, bind_vars)
        sort = get_sort_string(request.args.getlist('sort', []), attributes)
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', ARANGO_DEFAULT_LIMIT))

        query = prettify_aql(f'''
        WITH {get_all_collections(self.db_schema)}
        LET doc = DOCUMENT(@_id)
        FOR object, edge IN {depth_direction} doc @edge_collection
            {edge_filters}
            {type_filters}
            {search_filter}
            {filters}
            {sort}
            LIMIT {skip}, {limit}
            RETURN DISTINCT MERGE({fields}, {{_edge: UNSET(edge, "_id", "_key", "_rev", "_from", "_to")}})
        ''')
        results = db.aql(query, bind_vars=bind_vars, total=True)
        total = results['total']
        results = results['result']

        if results:
            _class = results[0]['_class']
            channel = f'pre_access_obj_{_class}'
            listeners = await get_listeners(channel, request)

            if listeners:
                results, _ = await pre_rpc(channel, listeners, results, request)

            if fields == 'object':
                results = [
                    translate_output(result, self.domain_cache[domain][result['_class']], self.db_schema)
                    for result in results
                ]
            elif '_class' not in request.args.getlist('field', []):
                for result in results:
                    del result['_class']

        results_obj = {
            'skip': skip,
            'limit': limit,
            'results_total': total,
            'results': results
        }

        log_perf.debug(f'REST relation list resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(results_obj, 200)

    async def relation_post_resolver(self, request, domain, domain_class, _key, relation):
        """Handler for domain object relation creation"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'create')

        db = await get_arangodb()
        service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('create_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        triggers = class_spec.get('triggers', [])
        _, edge_collection, direction = class_spec['relations'][relation]

        data = request.json
        _meta = data.pop('_meta', {})
        trx_id = request.headers.get('x-arango-trx-id')

        rel_key = None
        rel_class = data.pop('_class', None)
        rel_result = {}

        if rel_class:
            data = request.json.pop('_edge', {})
            rel_response = await self.domain_obj_post_resolver(request, domain, rel_class)

            if rel_response.status != 201:
                return rel_response

            if rel_response.body:
                rel_result = json.loads(rel_response.body.decode('utf-8'))
                rel_key = rel_result.get('_key')

        elif 'direction' in data:
            rel_class = data.pop('other_class')
            rel_key = data.pop('other_key')

        direction = data.pop('direction', direction)

        from_class = data.pop('from_class', rel_class if 'inbound' in direction else domain_class)
        from_spec = self.domain_cache[domain][from_class]
        from_key = data.pop('from_key', rel_key if 'inbound' in direction else _key)

        to_class = data.pop('to_class', rel_class if 'outbound' in direction else domain_class)
        to_spec = self.domain_cache[domain][to_class]
        to_key = data.pop('to_key', rel_key if 'outbound' in direction else _key)

        data = set_defaults(data, edge_collection, self.db_schema)
        data = {
            **data,
            '_from': f'{from_spec["resolver"]}/{from_key}',
            '_to': f'{to_spec["resolver"]}/{to_key}'
        }

        if 'set_creator' in triggers:
            data = set_creator(data, request)

        if 'set_created' in triggers:
            data = set_created(data)

        if 'set_updated' in triggers:
            data = set_updated(data)

        channel = f'pre_create_rel_{domain_class}_{relation}'
        listeners = service_rpcs.get(channel, [])

        if listeners:
            data['_meta'] = _meta
            data, trx_id = await pre_rpc(channel, listeners, data, request)
            request.headers['x-arango-trx-id'] = trx_id
            _meta = data.pop('_meta', _meta)

        query = prettify_aql(f'''
        INSERT {json.dumps(data)}
        IN @@collection
        RETURN {{ new: NEW }}
        ''')
        bind_vars = {
            '@collection': edge_collection,
        }
        result = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
        result = result['result'][0] if result['result'] else {}

        channel = f'post_create_rel_{domain_class}_{relation}'
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
            coro = partial(audit, {}, result['new'], request, True, note)
            task = request.app.add_task(coro)
            task.add_done_callback(task_handler)

        if rel_result:
            result = {k: v for k, v in result['new'].items() if k not in RESERVED_FIELDS}
            rel_result = translate_output(rel_result, domain_spec.get(rel_class), self.db_schema)
            result = {**rel_result, '_edge': result}
        else:
            result = result['new']

        log_perf.debug(f'REST relation post resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json(result, 201)

    async def relation_patch_resolver(self, request, domain, domain_class, _key, relation):
        """Handler for domain object relation creation"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'update')

        db = await get_arangodb()
        service_rpcs = await request.app.ctx.cache.get('service_rpcs', {})

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('update_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        triggers = class_spec.get('triggers', [])
        _, edge_collection, direction = class_spec['relations'][relation]

        data = request.json
        _meta = data.pop('_meta', {})
        trx_id = request.headers.get('x-arango-trx-id')

        direction = data.pop('direction', direction)
        from_class = data.pop('from_class', domain_class)
        from_spec = self.domain_cache[domain][from_class]
        from_key = data.pop('from_key', _key)
        to_class = data.pop('to_class', domain_class)
        to_spec = self.domain_cache[domain][to_class]
        to_key = data.pop('to_key', _key)

        if 'set_updated' in triggers:
            data = set_updated(data)

        channel = f'pre_update_rel_{domain_class}_{relation}'
        listeners = service_rpcs.get(channel, [])

        if listeners:
            data['_meta'] = _meta
            data, trx_id = await pre_rpc(channel, listeners, data, request)
            request.headers['x-arango-trx-id'] = trx_id
            _meta = data.pop('_meta', _meta)

        merge = 'true' if bool(request.args.get('merge_objects', False)) else 'false'
        query = prettify_aql(f'''
        FOR edge IN @@collection
            FILTER edge._from == @_from AND edge._to == @_to
            UPDATE edge WITH {json.dumps(data)}
            IN @@collection
            OPTIONS {{ mergeObjects: {merge} }}
            RETURN {{ old: OLD, new: NEW }}
        ''')
        bind_vars = {
            '@collection': edge_collection,
            '_from': f'{from_spec["resolver"]}/{from_key}',
            '_to': f'{to_spec["resolver"]}/{to_key}',
        }
        results = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
        results = results['result']

        if not results:
            raise InvalidUsage(results, 400)

        channel = f'post_update_rel_{domain_class}_{relation}'
        listeners = service_rpcs.get(channel, [])

        for result in results:

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
                coro = partial(audit, result['old'], result['new'], request, edge=True, note=note)
                task = request.app.add_task(coro)
                task.add_done_callback(task_handler)

        log_perf.debug(f'REST relation patch resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.empty()

    async def relation_delete_resolver(self, request, domain, domain_class, _key, relation):
        """Handler for domain object relation deletion"""

        if NO_DELETE:
            raise SanicException('Object deletions are disabled', 405)

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'delete')

        db = await get_arangodb()

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('delete_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        trx_id = request.headers.get('x-arango-trx-id')
        triggers = class_spec.get('triggers', [])

        _, edge_collection, direction = class_spec['relations'][relation]

        direction = request.args.get('direction', direction)

        from_class = request.args.get('from_class', domain_class)
        from_spec = self.domain_cache[domain][from_class]
        from_key = request.args.get('from_key', _key)

        to_class = request.args.get('to_class', domain_class)
        to_spec = self.domain_cache[domain][to_class]
        to_key = request.args.get('to_key', _key)

        query = prettify_aql('''
        FOR edge IN @@collection
            FILTER edge._from == @_from AND edge._to == @_to
            REMOVE edge IN @@collection
            RETURN { old: OLD }
        ''')
        bind_vars = {
            '@collection': edge_collection,
            '_from': f'{from_spec["resolver"]}/{from_key}',
            '_to': f'{to_spec["resolver"]}/{to_key}'
        }
        results = db.aql(query, bind_vars=bind_vars, trx_id=trx_id)
        results = results['result']

        if not results:
            raise InvalidUsage(results, 400)

        channel = f'post_delete_rel_{domain_class}_{relation}'
        listeners = await get_listeners(channel, request)

        for result in results:

            if listeners:
                coro = partial(post_rpc, channel, listeners, result['old'], {}, request)
                task = request.app.add_task(coro)
                task.add_done_callback(task_handler)

            if 'audit' in triggers:
                coro = partial(audit, result['old'], {}, request, edge=True, note=None)
                task = request.app.add_task(coro)
                task.add_done_callback(task_handler)

        log_perf.debug(f'REST relation delete resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.empty()

    async def neighbors_resolver(self, request, domain, domain_class, _key):
        """Handler for graph traversal starting at the given node, returning direct neighbors only"""
        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'read')

        db = await get_arangodb()
        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})

        all_edge_collections = get_all_edge_collections(self.db_schema)
        if not all_edge_collections:
            raise SanicException('No edge collections in schema', 404)

        all_relations = parse_all_relations(domain_spec)
        class_relations = all_relations.get(domain_class)

        if not class_relations:
            raise SanicException('domain class has no relations', 404)

        arango_obj_id = f'{class_spec["resolver"]}/{_key}'

        query = prettify_aql(f'''
        WITH {get_all_collections(self.db_schema)}
        FOR node, edge IN 0..1 ANY DOCUMENT(@_id)
            {all_edge_collections}
            RETURN {{ node, edge }}
        ''')
        bind_vars = { '_id': arango_obj_id }
        results = db.aql(query, bind_vars=bind_vars)
        results = results['result']

        nodes = []
        edges = []

        for result in results:
            node = result['node']
            edge = result['edge']

            node_id = node['_id']
            node_class = node['_class']

            node_class_spec = domain_spec.get(node_class)

            if not node_class_spec:
                continue

            translated_node = translate_output(node, node_class_spec, self.db_schema)
            translated_node['_id'] = node_id
            nodes.append(translated_node)

            if edge:
                edge_collection = edge['_id'].split('/')[0]
                edge_to = edge['_to']
                is_inbound = edge_to == arango_obj_id

                matched_class_relations = list(
                    filter(
                        lambda relation: relation.match_edge(edge_collection, is_inbound),
                        class_relations
                    )
                )
                matched_external_class_relations = list(
                    filter(
                        lambda relation: relation.match_edge(edge_collection, not is_inbound),
                        all_relations.get(node_class, [])
                    )
                )
                edge['_relations'] = list(relation.label for relation in matched_class_relations)
                edge['_external_relations'] = list(relation.label for relation in matched_external_class_relations)

                edges.append(edge)

        log_perf.debug(f'REST _neighbors resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        return response.json({'nodes': nodes, 'edges': edges}, 200)

    async def changes_resolver(self, request, domain, domain_class, _key):
        """Handler for domain object change log"""

        start = time.perf_counter() * 1000

        request.app.ctx.authorize(request, domain_class, 'read')

        db = await get_arangodb()

        domain_spec = self.domain_cache.get(domain, {})
        class_spec = domain_spec.get(domain_class, {})
        # get alias class_spec
        op_class = class_spec.get('read_class', domain_class)
        class_spec = domain_spec.get(op_class, class_spec)
        operations = class_spec.get('operations', OPERATIONS)
        triggers = class_spec.get('triggers', [])

        if not class_spec:
            raise NotFound(f'{domain_class} does not exist', 404)

        if 'audit' not in triggers:
            raise SanicException('No audit trigger registered for this domain class', 404)

        if 'read' not in operations:
            raise SanicException("Operation 'read' is not permitted for this domain class", 405)

        resolver = class_spec['resolver']
        attributes = {'created': 'created'}
        sort = get_sort_string(request.args.getlist('sort', ['-created']), attributes)
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', ARANGO_DEFAULT_LIMIT))
        edges = request.args.get('edges')

        edge_filters = prettify_aql('''
        OR object.from_id == @_id
        OR object.to_id == @_id
        ''') if edges else ''

        query = prettify_aql(f'''
        WITH audit_log
        FOR object IN audit_log
            FILTER object.changed_id == @_id
                {edge_filters}
            {sort}
            LIMIT {skip}, {limit}
            RETURN object
        ''')
        bind_vars = {'_id': f'{resolver}/{_key}'}
        results = db.aql(query, bind_vars=bind_vars, total=True)
        total = results['total']
        results = results['result']

        for update in results:
            update['pre'] = translate_output(update['pre'], class_spec, self.db_schema)
            update['post'] = translate_output(update['post'], class_spec, self.db_schema)

        log_perf.debug(f'REST _changes resolver time: {(time.perf_counter() * 1000 - start):.2f} ms')

        results_obj = {
            'skip': skip,
            'limit': limit,
            'results_total': total,
            'results': results
        }

        return response.json(results_obj, 200)
