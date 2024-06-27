import time
import logging

from decimal import Decimal
from importlib import import_module
from pathlib import Path

import jsonschema_rs as jsrs

from jinja2 import Template
from sanic.response import json, html
from sanic.exceptions import InvalidUsage, NotFound

from memoriam.config import ROOT_PATH
from memoriam.utils import load_raw, load_yaml


logging.getLogger('asyncio').setLevel(logging.ERROR)
logger = logging.getLogger('memoriam')
log_perf = logging.getLogger('memoriam.perf')

HTTP_METHODS = ['head', 'options', 'trace', 'get', 'post', 'put', 'patch', 'delete']


class OpenAPI:
    """A bare-bones API First OpenAPI extension with validation"""

    def __init__(self, app, namespace='default', spec_path=None, spec=None, schema_path=None, base_url=None):
        self.app = app
        self.base_url = base_url or '/api'
        self.spec_url = self.base_url + '/openapi.json'

        self.namespace = namespace
        self.specs = {}

        if spec_path:
            self.specs[namespace] = load_yaml(path=spec_path)
        elif spec:
            self.specs[namespace] = spec

        if schema_path:
            schema = load_yaml(path=schema_path)
            self.specs[namespace]['components']['schemas'] = {**schema['collections'], **schema['edge_collections']}

        template_path = Path(ROOT_PATH, 'templates', 'redoc.html').resolve()
        self.template = Template(load_raw(template_path))

        validation_schema_path = Path(ROOT_PATH, 'data', 'openapi_validation_schema.yml').resolve()
        self.validation_schema = load_yaml(path=validation_schema_path)

        self.validators = {}

        self.init_spec(namespace)

        app.add_route(self.openapi_ui, self.base_url)
        app.add_route(self.openapi_spec, self.spec_url)

        app.register_middleware(self.request_validator, 'request')

    def init_spec(self, namespace='default', spec=None, added_spec=None):
        """Initialize the OpenAPI extension"""
        if spec:
            self.specs[namespace] = spec

        if not self.specs.get(namespace):
            return

        start = time.perf_counter() * 1000
        added_info = ' (merging specs)' if added_spec else ''
        logger.debug(f'Rebuilding OpenAPI spec {namespace}{added_info}...')

        if added_spec:
            self.specs[namespace]['tags'].extend(added_spec['tags'])
            self.specs[namespace]['components']['parameters'].update(added_spec['components']['parameters'])
            self.specs[namespace]['components']['schemas'].update(added_spec['components']['schemas'])
            self.specs[namespace]['paths'].update(added_spec['paths'])

        jsrs.JSONSchema(self.validation_schema).validate(self.specs[namespace])

        for path, path_spec in self.specs[namespace]['paths'].items():

            full_path = self.base_url + path.replace('{', '<').replace('}', '>')
            full_path = full_path.replace('<namespace>', namespace)
            shared_params = path_spec.get('parameters', [])

            for method in HTTP_METHODS:
                method_spec = path_spec.get(method)
                if method_spec:

                    request_body = method_spec.get('requestBody', {})
                    operation_id = method_spec.get('operationId')
                    operation_params = method_spec.get('parameters', [])

                    validator_id = f'{full_path}:{method}'
                    self.validators[validator_id] = {}
                    self.validators[validator_id]['request_body'] = request_body
                    self.validators[validator_id]['parameters'] = shared_params + operation_params

                    if added_spec or not operation_id:  # stop here
                        continue

                    mod_path, name = operation_id.rsplit('.', 1)
                    module = import_module(mod_path)
                    function = getattr(module, name)

                    stream = False
                    for content_type in method_spec.get('requestBody', {}).get('content', {}):
                        stream = stream or content_type == 'application/octet-stream'

                    self.app.add_route(function, full_path, methods=[method.upper()], stream=stream)

        log_perf.debug(f'Rebuild OpenAPI spec time: {(time.perf_counter() * 1000 - start):.2f} ms')
        logger.debug(f'Rebuilt OpenAPI spec {namespace}{added_info}.')

    async def openapi_spec(self, request, namespace=''):
        """Serve the OpenAPI spec"""
        if not namespace:
            _, namespace, *_ = request.path.split('/')
            if not namespace or namespace == 'api':
                namespace = 'default'

        if namespace not in self.specs:
            raise NotFound(f'Namespace {namespace} does not exist', 404)

        return json(self.specs.get(namespace))

    async def openapi_ui(self, request, namespace=''):
        """Serve the OpenAPI UI"""
        if not namespace:
            _, namespace, *_ = request.path.split('/')
            if not namespace or namespace == 'api':
                namespace = 'default'

        if namespace not in self.specs:
            raise NotFound(f'Namespace {namespace} does not exist', 404)

        spec_url = self.spec_url.replace('<namespace>', namespace)
        index = self.template.render(spec_url=spec_url)
        return html(index)

    async def request_validator(self, request):
        """Resolve and jsonschema.validate rules given in OpenAPI spec"""
        namespace = ''
        if request.path:
            segments = request.path.split('/')
            if len(segments) > 1:
                namespace = segments[1]

        if not namespace or namespace == 'api':
            namespace = 'default'

        router_params = request.match_info
        validator_id = f'{request.path}:{request.method.lower()}'
        validator = self.validators.get(validator_id)

        # hack for accessing the right validator for RESTResolverEngine
        # TODO: not optimal
        if self.app.name == 'memoriam-domain' and not validator:
            validator_id = ''
            if 'domain' in router_params:
                validator_id += f'/{router_params["domain"]}/api'
            if 'domain_class' in router_params:
                validator_id += f'/{router_params["domain_class"]}'
            if '_key' in router_params:
                validator_id += '/<_key>'
            if 'relation' in router_params:
                validator_id += f'/{router_params["relation"]}'
            validator_id += f':{request.method.lower()}'
            validator = self.validators.get(validator_id)

        if validator:
            parameters = validator.get('parameters')
            request_body = validator.get('request_body')
            content = request_body.get('content', {})

            for parameter in parameters:
                parameter = self.ref_resolver(parameter, namespace)

                param_source = {}
                if parameter['in'] == 'path':
                    param_source = router_params
                elif parameter['in'] == 'query':
                    param_source = request.args
                elif parameter['in'] == 'header':
                    param_source = request.headers

                param_in = parameter['in'].title()
                param_name = parameter['name']
                param_value = param_source.get(param_name)
                param_schema = parameter.get('schema')
                param_type = param_schema.get('type')

                if parameter.get('required') and not param_value:
                    error_msg = f'{param_in} parameter {param_name} required, but not given'
                    logger.debug(error_msg)
                    raise InvalidUsage(error_msg, 400)

                if param_value and param_schema:
                    try:
                        if param_type == 'integer':
                            param_value = int(param_value)
                        elif param_type == 'number':
                            param_value = Decimal(param_value)
                        elif param_type == 'boolean':
                            param_value = param_value in ('true', 'yes', '1')
                        jsrs.JSONSchema(param_schema).validate(param_value)

                    except ValueError:
                        error_msg = f"'{param_name}'' is not of type '{param_type}'"
                        logger.debug(error_msg)
                        raise InvalidUsage(error_msg, 400) from None

            if request_body.get('required') and not request.body:
                error_msg = 'Request body required, but not given'
                logger.debug(error_msg)
                raise InvalidUsage(error_msg, 400)

            json_schema = content.get('application/json', {}).get('schema', {})
            json_schema = self.ref_resolver(json_schema, namespace)
            if json_schema:
                try:
                    jsrs.JSONSchema(json_schema).validate(request.json)
                except jsrs.ValidationError as error:
                    logger.debug(str(error))
                    raise InvalidUsage(str(error), 400) from None

    def ref_resolver(self, ref, namespace='default'):
        """Resolve internal $refs if found in parameter or schema"""
        if 'items' in ref:
            ref['items'] = self.ref_resolver(ref['items'], namespace)

        for poly in ('oneOf', 'allOf', 'anyOf'):
            if poly in ref:
                ref[poly] = [self.ref_resolver(item, namespace) for item in ref[poly]]

        if '$ref' not in ref:
            return ref

        _, *path = ref['$ref'].split('/')
        data = self.specs[namespace]
        for item in path:
            data = data[item]

        return data
