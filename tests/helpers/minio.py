import os
from minio import Minio


def get_minio_client():
    """Get a fresh Minio client"""
    return Minio(
        f'{os.getenv("LOCALHOST", "localhost")}:9000',
        access_key='minio',
        secret_key='miniosecret',
        secure=False
    )


def delete_all_objects_in_bucket(bucket_name):
    minio = get_minio_client()
    objects = minio.list_objects(bucket_name)
    for obj in objects:
        minio.remove_object(bucket_name, obj.object_name)


def delete_all_buckets():
    minio = get_minio_client()
    bucket_list = minio.list_buckets()
    for bucket in bucket_list:
        delete_all_objects_in_bucket(bucket.name)
        minio.remove_bucket(bucket.name)
