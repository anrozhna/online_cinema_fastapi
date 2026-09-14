import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from config.settings import Settings
from storages.interfaces import S3StorageInterface


class S3StorageClient(S3StorageInterface):
    """S3-compatible storage client works against MinIO or real AWS S3."""

    def __init__(self, settings: Settings) -> None:
        self._bucket_name = settings.S3_BUCKET_NAME
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.MINIO_ROOT_USER,
            aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def upload_file(self, file_data: bytes, file_name: str) -> str:
        self._client.put_object(Bucket=self._bucket_name, Key=file_name, Body=file_data)
        return self.get_file_url(file_name)

    def get_file_url(self, file_name: str) -> str:
        return f"{self._client.meta.endpoint_url}/{self._bucket_name}/{file_name}"

    def delete_file(self, file_name: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket_name, Key=file_name)
        except ClientError as e:
            raise RuntimeError(
                f"Failed to delete file '{file_name}' from storage."
            ) from e
