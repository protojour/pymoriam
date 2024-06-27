import logging

import imghdr

from sanic import response
from sanic.exceptions import NotFound, SanicException, InvalidUsage

from memoriam.authly import AUTHLY_URL
from memoriam.config import ARANGO_DOMAIN_DB_NAME
from memoriam.arangodb import get_arangodb, prettify_aql


logger = logging.getLogger('memoriam')


async def get_service(request):
    """Service data handler"""

    result = request.app.ctx.service_request('get', f'{AUTHLY_URL}/auth/session')
    service = result.json().get('profile', {})

    result = request.app.ctx.service_request('get', f'{AUTHLY_URL}/service/service')
    services = result.json() or []

    result = request.app.ctx.service_request('get', f'{AUTHLY_URL}/service/group')
    groups = result.json() or []

    result = request.app.ctx.service_request('get', f'{AUTHLY_URL}/service/user')
    users = result.json() or []

    service['services'] = services
    service['groups'] = groups
    service['users'] = users

    return response.json(service)


async def get_logo(request, service_name):
    """Service logo fetch handler (stand-in for Authly functionality)"""
    redis = request.app.ctx.redis
    logo = await redis.get(f'logo:{service_name}')

    if not logo:
        raise NotFound()

    image_type = imghdr.what('', h=logo)
    if image_type in ['png', 'gif', 'jpeg', 'webp']:
        content_type = 'image/' + image_type
    else:
        raise SanicException('Bad image data')

    return response.raw(body=logo, content_type=content_type)


async def post_logo(request, service_name):
    """Service logo upload handler (stand-in for Authly functionality)"""
    redis = request.app.ctx.redis
    file_ = request.files.get('file')

    if not file_ or not file_.body:
        raise InvalidUsage('Bad image data')

    logo = file_.body
    image_type = imghdr.what('', h=logo)

    if image_type not in ['png', 'gif', 'jpeg', 'webp']:
        raise InvalidUsage('Bad image data')

    await redis.set(f'logo:{service_name}', logo)

    return response.empty(201)


async def list_resources(request, domain_key):
    db = await get_arangodb(db_name=ARANGO_DOMAIN_DB_NAME)

    query = prettify_aql('''
    RETURN DOCUMENT(@_id)
    ''')
    bind_vars = {'_id': f'domain/{domain_key}'}
    result = db.aql(query, bind_vars=bind_vars)
    result = result['result'][0] if result['result'] else {}

    if not result:
        raise NotFound(f'domain/{domain_key} does not exist', 404)

    authly_resource_pointers = result['resources']

    authly_result = request.app.ctx.service_request('get', f'{AUTHLY_URL}/service/resource')
    authly_resources = authly_result.json()
    filtered_authly_resources = []
    if authly_resources:
        filtered_authly_resources = list(filter(lambda resource: str(resource['resourceName']) in authly_resource_pointers.values(), authly_resources))

    result_resources = []
    for resource in filtered_authly_resources:
        authly_resourcename = resource.pop('resourceName')
        for resourcename, resource_uuid in authly_resource_pointers.items():
            if authly_resourcename == resource_uuid:
                resource['resourceName'] = resourcename
                result_resources.append(resource)

    return response.json(result_resources, 200)


async def update_resource(request, domain_key):
    pass


async def delete_resource(request, domain_key):
    pass


async def get_roles(request):
    authly_result = request.app.ctx.service_request('get', f'{AUTHLY_URL}/service/group')

    if authly_result.status_code != 200:
        raise SanicException('Failed to get groups from authly', 500)

    return response.json(authly_result.json(), 200)


async def post_role(request, domain_key):
    pass


async def update_role(request, domain_key):
    pass


async def delete_role(request, domain_key):
    pass


async def get_policies(request, domain_key):
    pass


async def post_policy(request, domain_key):
    pass


async def update_policy(request, domain_key):
    pass


async def delete_policy(request, domain_key):
    pass
