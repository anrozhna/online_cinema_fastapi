from abc import ABC, abstractmethod


class S3StorageInterface(ABC):
    """Contract any S3-compatible storage client must satisfy."""

    @abstractmethod
    def upload_file(self, file_data: bytes, file_name: str) -> str:
        """Upload raw bytes under file_name, return the public/accessible URL."""
        raise NotImplementedError

    @abstractmethod
    def get_file_url(self, file_name: str) -> str:
        """Build the URL for a file already stored under file_name."""
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, file_name: str) -> None:
        raise NotImplementedError
