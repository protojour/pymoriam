import logging
from pathlib import Path

import ujson as json
import jsonschema_rs as jsrs

from memoriam.arangodb import get_arangodb, prettify_aql
from memoriam.config import (
    AUDIT_LOG_DB, ARANGO_HOST, ARANGO_HOSTS, ARANGO_PORT, ARANGO_SCHEME,
    ARANGO_ROOT_USERNAME, ARANGO_ROOT_PASSWORD,
    ARANGO_DB_NAME, ARANGO_SCHEMA_PATH,
    ARANGO_DOMAIN_DB_NAME, ARANGO_DOMAIN_SCHEMA_PATH,
    INDEX_CONFIG_PATH, SEARCH_CONFIG_PATH, ROOT_PATH,
    INIT_DB, INIT_SEARCH, UPDATE_SEARCH
)
from memoriam.utils import load_yaml, clean_str


logger = logging.getLogger('memoriam')


class ArangoInit:
    """Extension to initialize ArangoDB for Memoriam"""

    def __init__(self, app):
        self.app = app

        self.auth = (ARANGO_ROOT_USERNAME, ARANGO_ROOT_PASSWORD)
        self.hosts = (
            ARANGO_HOSTS.split(',')
            if ARANGO_HOSTS else
            [f'{ARANGO_SCHEME}://{ARANGO_HOST}:{ARANGO_PORT}']
        )

        self.search_config = load_yaml(path=SEARCH_CONFIG_PATH)
        validation_schema = load_yaml(path=Path(ROOT_PATH, 'data', 'search_config_validation_schema.yml').resolve())
        jsrs.JSONSchema(validation_schema).validate(self.search_config)

        self.view_name = self.search_config.get('view_name')
        self.view_props = self.search_config.get('view_props')
        self.index_fields = self.search_config.get('index_fields')
        self.analyzers = self.search_config.get('analyzers', [])

        if INIT_DB:
            app.register_listener(self.init_arangodb, 'main_process_start')

        if INIT_SEARCH:
            app.register_listener(self.init_analyzers, 'main_process_start')
            app.register_listener(self.init_search_view, 'main_process_start')

        if UPDATE_SEARCH:
            app.register_listener(self.run_update_search_indexes, 'main_process_ready')

    async def init_arangodb(self, app):
        """Initialize ArangoDB, create database, collections and indexes"""
        db = await get_arangodb(hosts=self.hosts, auth=self.auth)

        # init Domain metadata database and collections
        if not db.has_database(ARANGO_DOMAIN_DB_NAME):
            db.create_database(ARANGO_DOMAIN_DB_NAME)
            logger.info(f'Created database {ARANGO_DOMAIN_DB_NAME}')

        db.db_name = ARANGO_DOMAIN_DB_NAME

        schema = load_yaml(path=ARANGO_DOMAIN_SCHEMA_PATH)
        db_validation_schema = load_yaml(path=Path(ROOT_PATH, 'data', 'db_schema_validation_schema.yml').resolve())
        jsrs.JSONSchema(db_validation_schema).validate(schema)

        for collection in schema['collections']:
            if not db.has_collection(collection):
                db.create_collection(collection)
                logger.info(f'Created collection {collection}')

        for collection in schema['edge_collections']:
            if not db.has_collection(collection):
                db.create_collection(collection, edge=True)
                logger.info(f'Created edge collection {collection}')

        # init main database
        if not db.has_database(ARANGO_DB_NAME):
            db.create_database(ARANGO_DB_NAME)
            logger.info(f'Created database {ARANGO_DB_NAME}')

        db.db_name = ARANGO_DB_NAME

        db_schema = load_yaml(path=ARANGO_SCHEMA_PATH)
        jsrs.JSONSchema(db_validation_schema).validate(db_schema)

        index_config = load_yaml(path=INDEX_CONFIG_PATH)
        index_validation_schema = load_yaml(path=Path(ROOT_PATH, 'data', 'index_config_validation_schema.yml').resolve())
        jsrs.JSONSchema(index_validation_schema).validate(index_config)

        if AUDIT_LOG_DB:
            audit_schema = load_yaml(path=Path(ROOT_PATH, 'data', 'db_schema_audit.yml').resolve())
            jsrs.JSONSchema(db_validation_schema).validate(audit_schema)

            db_schema['collections']['audit_log'] = audit_schema['collections']['audit_log']

        def add_indexes(collection, edge=False):
            logged = False

            # get stored indexes
            indexes = db.list_indexes(collection).get('result', [])
            indexes_by_field = {}
            for index in indexes:
                for field in index.get('fields'):
                    indexes_by_field[field] = index

            if '_class' not in indexes_by_field:
                logger.info(f'Adding indexes for {collection}...')
                logged = True
                data = {
                    'type': 'persistent',
                    'fields': ['_class'],
                    'inBackground': True,
                }
                db.create_index(collection, data)

            batch = 'collections' if not edge else 'edge_collections'
            fields = index_config.get(batch, {}).get(collection, {})

            for field_name, field_spec in fields.items():

                # get stored index for field and normalize for comparison
                stored_index = indexes_by_field.get(field_name, {})
                stored_index.pop('id', None)
                stored_index.pop('name', None)
                stored_index.pop('fields', None)

                # compare field spec with stored index (merging defaults)
                # add index only if different from stored index
                if {**stored_index, **field_spec} != stored_index:

                    if not logged:
                        logger.info(f'Adding indexes for {collection}...')
                        logged = True

                    field_spec['fields'] = [field_name]
                    field_spec['inBackground'] = field_spec.get('inBackground', True)  # set default
                    db.create_index(collection, field_spec)

        # init main database collections and indexes
        for collection in db_schema['collections']:
            if not db.has_collection(collection):
                db.create_collection(collection)
                logger.info(f'Created collection {collection}')

        for collection in db_schema['collections']:
            add_indexes(collection)

        for collection in db_schema['edge_collections']:
            if not db.has_collection(collection):
                db.create_collection(collection, edge=True)
                logger.info(f'Created edge collection {collection}')

        for collection in db_schema['edge_collections']:
            add_indexes(collection, edge=True)

    async def init_analyzers(self, app):
        """Initialize configured analyzers"""
        db = await get_arangodb(hosts=self.hosts, auth=self.auth)

        analyzers = db.list_analyzers()
        analyzers_dict = {alyz.get('name'): alyz for alyz in analyzers.get('result', [])}

        for analyzer in self.analyzers:
            analyzer_name = analyzer['name']
            stored_analyzer = analyzers_dict.get(analyzer_name)

            if stored_analyzer:
                stored_props = stored_analyzer.get('properties')
                analyzer_props = analyzer.get('properties')

                if not stored_props == analyzer_props:
                    logger.info(f'Analyzer {analyzer_name} is outdated, deleting.')
                    db.delete_analyzer(analyzer_name)
                    db.create_analyzer(analyzer)
                    logger.info(f'Analyzer {analyzer_name} created.')
            else:
                db.create_analyzer(analyzer)
                logger.info(f'Analyzer {analyzer_name} not found, created.')

    async def init_search_view(self, app):
        """Initialize or update configured search view"""
        db = await get_arangodb(hosts=self.hosts, auth=self.auth)

        views = db.list_views()
        views_dict = {view.get('name'): view for view in views.get('result', [])}

        if self.view_name in views_dict:
            stored_view = views_dict[self.view_name]
            stored_links = stored_view.get('links', {})
            new_links = self.view_props.get('links', {})

            if stored_links.keys() != new_links.keys():
                db.update_view(self.view_name, self.view_props)
                logger.info(f'Search view {self.view_name} updated.')
        else:
            db.create_view({
                'name': self.view_name,
                'type': 'arangosearch',
                **self.view_props
            })
            logger.info(f'Search view {self.view_name} not found, created.')

    async def run_update_search_indexes(self, app):
        """Run update_search_indexes as a background process"""
        db = await get_arangodb(hosts=self.hosts, auth=self.auth)

        logger.info('Updating search indexes...')
        for collection, indexed_fields in self.index_fields.items():
            query = prettify_aql('''
            FOR object IN @@collection
                RETURN object
            ''')
            bind_vars = {
                '@collection': collection,
            }
            results = db.aql(query, bind_vars=bind_vars)
            results = results['result']

            logger.info(f'Updating search indexes for {collection}...')
            for obj in results:
                _index = ' '.join([clean_str(obj.get(field)) for field in indexed_fields])

                # update only if necessary (simplest possible hash comparison)
                if hash(_index) != hash(obj.get('_index')):
                    update = {
                        '_key': obj['_key'],
                        '_index': _index,
                    }
                    query = prettify_aql(f'''
                    UPDATE {json.dumps(update)}
                    IN @@collection
                    ''')
                    db.aql(query, bind_vars=bind_vars)
