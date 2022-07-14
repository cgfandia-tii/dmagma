import pathlib
from typing import Iterable

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from backend import config, exceptions


class StorageException(exceptions.BackendException):
    """Basic storage exception"""

    pass


class NotFoundException(StorageException):
    """Storage not found exception"""

    pass


class Storage:
    def put(self, file: pathlib.Path, key: str):
        raise NotImplementedError()

    def get(self, key: str, file: pathlib.Path):
        raise NotImplementedError()

    def list(self, prefix: str = None) -> Iterable[str]:
        raise NotImplementedError()

    def delete(self, key: str):
        raise NotImplementedError()

    def clear(self):
        raise NotImplementedError()


class S3StorageException(StorageException):
    """S3(boto3) errors wrapper"""

    pass


class S3NotFoundException(S3StorageException, NotFoundException):
    pass


def boto_errors_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error = e.response.get("Error", None)
            if error:
                message = error.get("Message", None)
                if message == "Not Found":
                    raise S3NotFoundException()
            raise S3StorageException(str(e))
        except BotoCoreError as e:
            raise S3StorageException(str(e))

    return wrapper


class S3Storage(Storage):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        region: str,
        bucket: str,
        max_retries: int = 5,
    ):
        retries = {"max_attempts": max_retries, "mode": "standard"}
        self._s3 = boto3.resource(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", retries=retries),
            region_name=region,
        )
        self._bucket = bucket
        self._bucket_created = False

    @property
    def bucket(self) -> str:
        return self._bucket

    def _exists(self) -> bool:
        try:
            self._s3.meta.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            return False
        return True

    @boto_errors_handler
    def put(self, file: pathlib.Path, key: str):
        if not self._bucket_created:
            try:
                self._s3.create_bucket(Bucket=self.bucket)
            except (
                self._s3.meta.client.exceptions.BucketAlreadyOwnedByYou,
                self._s3.meta.client.exceptions.BucketAlreadyExists,
            ):
                pass
            self._bucket_created = True
        self._s3.meta.client.upload_file(str(file.absolute()), self.bucket, key)

    @boto_errors_handler
    def get(self, key: str, file: pathlib.Path):
        self._s3.meta.client.download_file(self.bucket, key, str(file.absolute()))

    @boto_errors_handler
    def list(self, prefix: str = None) -> Iterable[str]:
        if prefix:
            objects = self._s3.Bucket(self.bucket).objects.filter(Prefix=prefix)
        else:
            objects = self._s3.Bucket(self.bucket).objects.all()
        for obj in objects:
            yield obj.key

    @boto_errors_handler
    def delete(self, key: str):
        self._s3.meta.client.delete_object(Bucket=self.bucket, Key=key)

    @boto_errors_handler
    def clear(self):
        if self._exists():
            for key in self.list():
                self.delete(key)
            self._s3.Bucket(self.bucket).delete()


def s3_factory(bucket: str) -> S3Storage:
    return S3Storage(
        config.S3_ENDPOINT,
        config.S3_ACCESS_KEY,
        config.S3_SECRET_KEY,
        config.S3_REGION,
        bucket,
    )
