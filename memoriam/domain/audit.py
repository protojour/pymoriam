import logging
from pathlib import Path

from sanic import response

from memoriam.config import AUDIT_LOG, AUDIT_LOG_DB, AUDIT_VERSIONING, ROOT_PATH, ARANGO_DEFAULT_LIMIT
from memoriam.arangodb import get_arangodb, prettify_aql, get_sort_string
from memoriam.domain.triggers import generate_audit
from memoriam.utils import load_yaml


logger = logging.getLogger('memoriam')
log_audit = logging.getLogger('memoriam.audit')


class AuditLog:
    """This Sanic extension initializes audit logger paths"""

    def __init__(self, app, openapi):
        if not AUDIT_LOG_DB:
            return

        spec_path = Path(ROOT_PATH, 'data', 'openapi_spec_audit.yml').resolve()
        self.spec = load_yaml(path=spec_path)

        openapi.init_spec(namespace='system', added_spec=self.spec)

        app.add_route(
            handler=self.post_audit_log,
            uri='/system/api/audit_log',
            methods=['POST']
        )
        app.add_route(
            handler=self.get_audit_log,
            uri='/system/api/audit_log/<collection>/<_key>',
            methods=['GET']
        )

    async def post_audit_log(self, request):
        """Handler for manual audit logging"""
        request.app.ctx.authorize(request, 'audit', 'create')

        db = await get_arangodb()

        data = request.json
        trx_id = request.headers.get('x-arango-trx-id')
        audit_logs = []

        for item in data:
            pre = item.get('pre')
            post = item.get('post')
            edge = item.get('edge', False)
            note = item.get('note')

            if not (pre.get('_id') or post.get('_id')):
                logger.warn("Audit is missing pre['_id'] or post['_id'], no audit logged!")

            audit_log = generate_audit(pre, post, request, edge, note)
            if audit_log:
                audit_logs.append(audit_log)

                if AUDIT_LOG:
                    log_audit.info(f'Audit: {audit_log}')

        results = db.bulk_create('audit_log', audit_logs, trx_id=trx_id)

        audit_logs = []
        audits_by_changed_collection = {}

        for result in results:
            audit = result['new']
            audit_logs.append(audit)

            if AUDIT_VERSIONING and audit.get('post'):
                audit_id = audit['_id']
                changed_id = audit['changed_id']
                changed_coll, changed_key = changed_id.split('/', 1)

                if not audits_by_changed_collection.get(changed_coll):
                    audits_by_changed_collection[changed_coll] = []

                audits_by_changed_collection[changed_coll].append({
                    '_key': changed_key,
                    '_version': audit_id,
                })

        for coll, audits in audits_by_changed_collection.items():
            results = db.bulk_update(coll, audits, trx_id=trx_id)

        return response.json(audit_logs, 201)

    async def get_audit_log(self, request, collection, _key):
        """Handler for audit logs for specific _id"""
        request.app.ctx.authorize(request, 'audit', 'read')

        db = await get_arangodb()

        attributes = {'created': 'created'}
        sort = get_sort_string(request.args.getlist('sort', ['created']), attributes, obj_name='audit')
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', ARANGO_DEFAULT_LIMIT))
        edges = request.args.get('edges')

        edge_filters = prettify_aql('''
        OR audit.from_id == @_id
        OR audit.to_id == @_id
        ''') if edges else ''

        query = prettify_aql(f'''
        WITH audit_log
        FOR audit IN audit_log
            FILTER audit.changed_id == @_id
                {edge_filters}
            {sort}
            LIMIT {skip}, {limit}
            RETURN audit
        ''')
        bind_vars = {'_id': f'{collection}/{_key}'}
        results = db.aql(query, bind_vars=bind_vars, total=True)
        total = results['total']
        results = results['result']

        results_obj = {
            'skip': skip,
            'limit': limit,
            'results_total': total,
            'results': results
        }

        return response.json(results_obj, 200)
