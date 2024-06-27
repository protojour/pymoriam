import logging

import ujson as json
import yaml

from caseconverter import snakecase

from memoriam.arangodb import get_arangodb, prettify_aql
from memoriam.config import (
    DOMAIN_SCHEMA_PATH, ARANGO_DOMAIN_DB_NAME
)
from memoriam.utils import Dumper, Request, load_yaml, iso8601_now
from memoriam.domain.domain import validate_domain


logger = logging.getLogger('memoriam')


class DomainInit:
    """Extension to initialize Domains for Memoriam"""

    def __init__(self, app):
        self.app = app

        self.domain_schema = load_yaml(path=DOMAIN_SCHEMA_PATH)
        label = self.domain_schema.get('label')
        schema = self.domain_schema.get('schema')

        if label and schema:
            self.domain_schema['schema'] = yaml.dump(schema, sort_keys=False, Dumper=Dumper)
            app.register_listener(self.init_domain, 'main_process_start')

    async def init_domain(self, app):
        """Initialize ArangoDB, create database, collections and indexes"""
        label = self.domain_schema.get('label')
        _key = snakecase(label)

        request = Request(json=self.domain_schema, app=app)
        logger.info(f'Validating root domain {label}')
        await validate_domain(request, _key=_key)

        self.domain_schema['_key'] = _key
        self.domain_schema['updated'] = iso8601_now()

        db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)
        query = prettify_aql(f'''
        UPSERT {{ _key: @_key }}
        INSERT {json.dumps(self.domain_schema)}
        REPLACE {json.dumps(self.domain_schema)}
        IN domain
        RETURN {{ type: OLD ? 'replace' : 'insert' }}
        ''')
        bind_vars = {'_key': _key}

        result = db.aql(query, bind_vars=bind_vars)
        result = result['result'][0] if result['result'] else {}

        if result.get('type') == 'insert':
            logger.info(f'Added root domain {label}')
        if result.get('type') == 'replace':
            logger.info(f'Updated root domain {label}')

        # domain schema cache invalidation
        redis = app.ctx.redis
        await redis.delete('memoriam_graphql_schemas')
        await redis.delete('memoriam_rest_schemas')
