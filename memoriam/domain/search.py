import logging

import ujson as json
from sanic import response

from memoriam.arangodb import (
    get_arangodb, prettify_aql, get_relation_attributes,
    get_filter_strings, get_all_collections, translate_output
)
from memoriam.config import SEARCH_CONFIG_PATH, ARANGO_SCHEMA_PATH, ARANGO_DEFAULT_LIMIT
from memoriam.utils import load_yaml, clean_str


logger = logging.getLogger('memoriam')


class ArangoSearch:
    """A Memoriam extension enabling ArangoSearch functionality"""

    def __init__(self, app):
        self.app = app
        self.app.ctx.search = self

        self.config = load_yaml(path=SEARCH_CONFIG_PATH)

        self.view_name = self.config.get('view_name')
        self.view_props = self.config.get('view_props')
        self.index_fields = self.config.get('index_fields')
        self.analyzers = self.config.get('analyzers', [])

    def get_search_subset(self, search_query, class_spec, bind_vars, all_=False):
        """Get an AQL search query subset for the given Domain search query.
           Will mutate bind_vars!"""
        if not search_query:
            return ''

        collections = f'["{class_spec["resolver"]}"]'
        if all_:
            collections = json.dumps(list(self.view_props.get('links')))

        search_subset = f'''
        LET {class_spec["resolver"]} = (
            FOR result IN {self.view_name}
                SEARCH ANALYZER(result._index IN TOKENS(@search, "text_en"), "text_en")
                OPTIONS {{ waitForSync: true, collections: {collections} }}
                RETURN result
        )
        '''
        bind_vars['search'] = search_query

        return search_subset

    def build_search_index(self, collection, obj):
        """Build _index field from configured indexed fields"""
        indexed_fields = self.index_fields.get(collection, [])
        return ' '.join([clean_str(obj.get(field)) for field in indexed_fields])


async def cross_domain_search(request):
    """Handler for cross-domain search"""

    db_schema = load_yaml(path=ARANGO_SCHEMA_PATH)
    db = await get_arangodb()
    domain_cache = await request.app.ctx.cache.get('domain_cache')
    merged_spec = {key: val for domain in domain_cache.values() for key, val in domain.items()}

    class_spec = {
        'resolver': 'search',
        'relations': {
            'search': ['ANY', None, None]
        }
    }

    bind_vars = {}
    search_subset = request.app.ctx.search.get_search_subset(request.args.get('search'), class_spec, bind_vars, all_=True)
    attributes = get_relation_attributes(merged_spec, class_spec, 'search')
    filters = get_filter_strings(request.args.getlist('filter', []), attributes, bind_vars)
    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', ARANGO_DEFAULT_LIMIT))

    query = prettify_aql(f'''
    WITH {get_all_collections(db_schema)}
    {search_subset}
    FOR object IN search
        {filters}
        SORT TFIDF(object) DESC
        LIMIT {skip}, {limit}
        RETURN object
    ''')
    results = db.aql(query, bind_vars=bind_vars, total=True)
    total = results['total']
    results = results['result']

    results = [
        translate_output(result, merged_spec.get(result.get('_class'), {}), db_schema)
        for result in results
    ]
    results_obj = {
        'skip': skip,
        'limit': limit,
        'results_total': total,
        'results': results
    }

    return response.json(results_obj, 200)
