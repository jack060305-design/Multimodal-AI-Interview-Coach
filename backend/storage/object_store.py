import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from config import get_settings


class ObjectStore(ABC):
    @abstractmethod
    def upload(self, data: bytes, filename: str, content_type: str = "video/webm") -> str:
        pass

    @abstractmethod
    def get_url(self, key: str) -> str | None:
        pass


class LocalObjectStore(ObjectStore):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, data: bytes, filename: str, content_type: str = "video/webm") -> str:
        ext = Path(filename).suffix or ".webm"
        key = f"{uuid.uuid4()}{ext}"
        path = self.base_dir / key
        path.write_bytes(data)
        return key

    def get_url(self, key: str) -> str | None:
        path = self.base_dir / key
        return str(path) if path.exists() else None


class S3ObjectStore(ObjectStore):
    def __init__(self):
        import boto3

        settings = get_settings()
        session = boto3.session.Session(
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region,
        )
        kwargs = {}
        if settings.s3_endpoint_url:
            kwargs["endpoint_url"] = settings.s3_endpoint_url
        self.client = session.client("s3", **kwargs)
        self.bucket = settings.s3_bucket

    def upload(self, data: bytes, filename: str, content_type: str = "video/webm") -> str:
        ext = Path(filename).suffix or ".webm"
        key = f"videos/{uuid.uuid4()}{ext}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def get_url(self, key: str) -> str | None:
        settings = get_settings()
        if settings.s3_endpoint_url:
            return f"{settings.s3_endpoint_url.rstrip('/')}/{self.bucket}/{key}"
        return f"https://{self.bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def get_object_store() -> ObjectStore:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3ObjectStore()
    return LocalObjectStore(settings.local_storage_dir)
