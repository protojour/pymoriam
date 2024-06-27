import hashlib
import io
import logging
import typing

from sanic import response
from sanic.exceptions import SanicException, InvalidUsage, NotFound, PayloadTooLarge
from minio import Minio
from minio.datatypes import Part
from minio.error import S3Error
from minio.helpers import MIN_PART_SIZE, DictType

from memoriam.utils import trueish
from memoriam.config import (
    MINIO_HOST, MINIO_PORT, MINIO_TLS, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_MAX_FILESIZE
)


STREAM_PARTS_SIZE = 1024 * 1024 * 10

logger = logging.getLogger('memoriam')


def get_minio_client():
    """Get a fresh Minio client"""
    return Minio(
        f'{MINIO_HOST}:{MINIO_PORT}',
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=MINIO_TLS
    )


async def list_buckets(request):
    """List all buckets"""
    request.app.ctx.authorize(request, 'storage', 'read_buckets')

    minio = get_minio_client()

    buckets = [{
        'bucket_name': b.name,
        'creation_date': str(b.creation_date)
    } for b in minio.list_buckets()]

    if not buckets:
        error = 'No buckets found'
        logger.debug(error)
        raise NotFound(error, 404)

    return response.json(buckets)


async def post_bucket(request):
    """Add new bucket"""
    request.app.ctx.authorize(request, 'storage', 'create_bucket')

    minio = get_minio_client()
    bucket_name = request.json.get('bucket_name')

    if minio.bucket_exists(bucket_name):
        error = f'Bucket {bucket_name} already exists'
        logger.debug(error)
        raise SanicException(error, 409)

    minio.make_bucket(bucket_name)
    return response.json('', 201)


async def get_bucket(request, bucket_name):
    """List contents of bucket"""
    request.app.ctx.authorize(request, 'storage', 'read_bucket')

    minio = get_minio_client()

    if not minio.bucket_exists(bucket_name):
        error = f'Bucket {bucket_name} does not exist'
        logger.debug(error)
        raise NotFound(error, 404)

    objects = [{
        'object_name': obj.object_name,
        'size': obj.size,
        'etag': obj.etag,
        'content_type': obj.content_type,
        'last_modified': str(obj.last_modified),
        'metadata': obj.metadata,
    } for obj in minio.list_objects(bucket_name)]

    return response.json(objects)


async def post_object(request, bucket_name, object_name):
    """Add new object to bucket"""
    request.app.ctx.authorize(request, 'storage', 'create_object')

    minio = get_minio_client()

    if not minio.bucket_exists(bucket_name):
        error = f'Bucket {bucket_name} does not exist'
        logger.debug(error)
        raise NotFound(error, 404)

    try:
        minio.stat_object(bucket_name, object_name)
        error = f'Object {object_name} already exists'
        logger.debug(error)
        raise SanicException(error, 409)
    except S3Error as error:
        if error.code == 'NoSuchKey':
            pass
        else:
            raise

    metadata = {}

    if ('content-type' in request.headers and
        request.headers['content-type'] == 'application/octet-stream'):

        headers = {'Content-Type': 'application/octet-stream'}

        done = False
        upload_id = None
        parts = []
        part_number = 1
        part_data = b''

        try:
            upload_id = minio._create_multipart_upload(
                bucket_name=bucket_name,
                object_name=object_name,
                headers=typing.cast(DictType, headers)
            )
            while not done:
                data = await request.stream.read()

                if not data:
                    done = True

                if data or done:

                    if data:
                        part_data += data

                    if len(part_data) < MIN_PART_SIZE and not done:
                        continue

                    etag = minio._upload_part(
                        bucket_name=bucket_name,
                        object_name=object_name,
                        data=part_data,
                        headers=typing.cast(DictType, headers),
                        upload_id=upload_id,
                        part_number=part_number
                    )
                    parts.append(Part(part_number, etag))
                    part_number += 1
                    part_data = b''

            result = minio._complete_multipart_upload(
                bucket_name=bucket_name,
                object_name=object_name,
                upload_id=upload_id,
                parts=parts
            )

        except Exception as exc:
            if upload_id:
                minio._abort_multipart_upload(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    upload_id=upload_id
                )
            raise exc

    else:
        await request.receive_body()
        if 'file' not in request.files:
            error = 'No file supplied'
            logger.debug(error)
            raise InvalidUsage(error, 400)

        file = request.files.get('file')

        if len(file.body) > MINIO_MAX_FILESIZE:
            error = f'Maximum object file size is {MINIO_MAX_FILESIZE}. Use stream instead.'
            logger.debug(error)
            raise PayloadTooLarge(error, 413)

        file_hash = hashlib.sha256(file.body)
        metadata = {'sha256': file_hash.hexdigest()}
        result = minio.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=io.BytesIO(file.body),
            length=len(file.body),
            content_type=file.type,
            metadata=typing.cast(DictType, metadata)
        )

    return response.json({**metadata, 'object_name': object_name, 'etag': result.etag}, 201)


async def get_object(request, bucket_name, object_name):
    """Get object from bucket"""
    request.app.ctx.authorize(request, 'storage', 'read_object')

    minio = get_minio_client()

    if not minio.bucket_exists(bucket_name):
        error = f'Bucket {bucket_name} does not exist'
        logger.debug(error)
        raise NotFound(error, 404)

    try:
        stat = minio.stat_object(bucket_name, object_name)
    except S3Error as error:
        error = f'Object {object_name} does not exist'
        logger.debug(error)
        raise NotFound(error, 404) from None

    if trueish(request.args.get('stat', False)):
        return response.json({
            'object_name': stat.object_name,
            'size': stat.size,
            'etag': stat.etag,
            'content_type': stat.content_type,
            'last_modified': str(stat.last_modified),
            'metadata': stat.metadata,
        })

    stat_size = stat.size or 0
    if stat_size < MINIO_MAX_FILESIZE:
        obj = minio.get_object(bucket_name, object_name)
        return response.HTTPResponse(obj.read(), content_type=obj.getheader('Content-Type'))

    async def async_stream(response):
        streamed_size = 0
        part_size = STREAM_PARTS_SIZE

        stat_size = stat.size or 0
        while streamed_size != stat_size:
            await response.write(
                minio.get_object(
                    bucket_name,
                    object_name,
                    offset=streamed_size,
                    length=part_size
                ).read()
            )
            streamed_size += part_size
            if stat_size - streamed_size < STREAM_PARTS_SIZE:
                part_size = stat_size - streamed_size

    return response.ResponseStream(async_stream, content_type='text/csv')
