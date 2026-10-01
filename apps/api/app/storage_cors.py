"""Bucket rules for private S3/R2 storage behind direct upload.

CORS lets the Karma browser POST direct uploads (presigned POST, size capped by the policy)
and GET media. A lifecycle rule expires abandoned staging objects under `uploads/` after a
day, since only upload-complete moves a file out of staging.

Prints the rules derived from KARMA_ALLOWED_ORIGINS; --apply writes them to S3_BUCKET.
Run by an operator, never at application start:

    python -m app.storage_cors            # show
    python -m app.storage_cors --apply    # write
"""

import json
import sys

from app.config import settings
from app.services.uploads import STAGING_PREFIX

STAGING_RULE_ID = "expire-direct-upload-staging"


def cors_configuration(origins):
    if not origins:
        raise ValueError("KARMA_ALLOWED_ORIGINS is empty")
    return {
        "CORSRules": [
            {
                "AllowedOrigins": list(origins),
                "AllowedMethods": ["POST", "GET"],
                "AllowedHeaders": ["Content-Type"],
                "MaxAgeSeconds": 600,
            }
        ]
    }


def staging_rule():
    return {
        "ID": STAGING_RULE_ID,
        "Filter": {"Prefix": f"{STAGING_PREFIX}/"},
        "Status": "Enabled",
        "Expiration": {"Days": 1},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
    }


def lifecycle_configuration(existing_rules=()):
    """The bucket's lifecycle with the staging rule set; other rules are kept as they are,
    because a lifecycle write replaces the whole configuration."""
    others = [rule for rule in existing_rules if rule.get("ID") != STAGING_RULE_ID]
    return {"Rules": [*others, staging_rule()]}


def current_rules(s3, bucket):
    try:
        return s3.get_bucket_lifecycle_configuration(Bucket=bucket).get("Rules", [])
    except s3.exceptions.ClientError as error:
        if error.response.get("Error", {}).get("Code") == "NoSuchLifecycleConfiguration":
            return []
        raise


def main(argv):
    from app.services.storage import Storage

    cfg = settings()
    cors = cors_configuration(cfg.karma_origins)
    storage = Storage() if "--apply" in argv else None
    if storage is not None and not storage.s3:
        raise SystemExit("Local storage serves CORS from the API; nothing to apply.")
    existing = current_rules(storage.s3, cfg.s3_bucket) if storage else []
    lifecycle = lifecycle_configuration(existing)
    print(json.dumps({"cors": cors, "lifecycle": lifecycle}, indent=2))
    if storage:
        storage.s3.put_bucket_cors(Bucket=cfg.s3_bucket, CORSConfiguration=cors)
        storage.s3.put_bucket_lifecycle_configuration(
            Bucket=cfg.s3_bucket, LifecycleConfiguration=lifecycle
        )


if __name__ == "__main__":
    main(sys.argv[1:])
