"""Ensure S3 bucket exists (AWS / MinIO / compatible endpoints)."""

from __future__ import annotations

import logging

from config import get_settings

logger = logging.getLogger(__name__)


def ensure_s3_bucket() -> bool:
    settings = get_settings()
    if settings.storage_backend != "s3":
        return False
    try:
        import boto3

        session = boto3.session.Session(
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region,
        )
        kwargs: dict = {}
        if settings.s3_endpoint_url:
            kwargs["endpoint_url"] = settings.s3_endpoint_url
        client = session.client("s3", **kwargs)
        buckets = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
        if settings.s3_bucket not in buckets:
            create_kwargs: dict = {"Bucket": settings.s3_bucket}
            if not settings.s3_endpoint_url:
                create_kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": settings.aws_region
                    if settings.aws_region != "us-east-1"
                    else "us-west-2"
                }
            try:
                client.create_bucket(**create_kwargs)
            except Exception:
                client.create_bucket(Bucket=settings.s3_bucket)
            logger.info("Created S3 bucket %s", settings.s3_bucket)
        return True
    except Exception as exc:
        logger.warning("S3 bucket check skipped: %s", exc)
        return False
