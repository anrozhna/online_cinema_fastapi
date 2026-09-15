import asyncio

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from config.settings import Settings

# Імпортуємо ваші кастомні помилки з пакету exceptions
from exceptions.storage import S3ConnectionError, S3FileNotFoundError, S3FileUploadError
from storages.interfaces import S3StorageInterface


class S3StorageClient(S3StorageInterface):
    """
    S3-compatible storage client working against MinIO or real AWS S3.

    boto3 itself is synchronous — each call is offloaded to a worker
    thread via asyncio.to_thread so it doesn't block the event loop.
    """

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

    async def upload_file(self, file_data: bytes, file_name: str) -> str:
        """
        Upload raw binary file data to the specified S3 bucket path securely.

        Raises:
            S3ConnectionError: If there is a network or connection issue.
            S3FileUploadError: If the bucket operation fails.
        """
        try:
            await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket_name,
                Key=file_name,
                Body=file_data,
                ContentType="image/jpeg",
            )
        except (ConnectionError, TimeoutError) as e:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage during upload: {e}"
            ) from e
        except (BotoCoreError, ClientError) as e:
            raise S3FileUploadError(
                f"Failed to upload file '{file_name}' to S3: {e}"
            ) from e

        return await self.get_file_url(file_name)

    async def get_file_url(self, file_name: str) -> str:
        """Generate a fully qualified public URL link to read the stored asset."""
        # No blocking I/O involved — kept async only to satisfy the
        # interface and stay consistent with the other methods.
        return f"{self._client.meta.endpoint_url}/{self._bucket_name}/{file_name}"

    async def delete_file(self, file_name: str) -> None:
        """
        Delete a file from the S3 storage bucket.

        Raises:
            S3FileNotFoundError: If the requested key does not exist.
            S3ConnectionError: If connection fails.
        """
        try:
            await asyncio.to_thread(
                self._client.delete_object,
                Bucket=self._bucket_name,
                Key=file_name,
            )
        except (ConnectionError, TimeoutError) as e:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage during deletion: {e}"
            ) from e
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("NoSuchKey", "404"):
                raise S3FileNotFoundError(
                    f"Requested file '{file_name}' not found in S3."
                ) from e
            raise S3FileUploadError(
                f"Failed to delete file '{file_name}' from storage: {e}"
            ) from e
