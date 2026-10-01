"""CORS for private S3/R2 storage, so the Karma browser can PUT direct uploads and GET media.

Prints the bucket rules derived from KARMA_ALLOWED_ORIGINS; --apply writes them to S3_BUCKET.
Run by an operator, never at application start:

    python -m app.storage_cors            # show
    python -m app.storage_cors --apply    # write
"""

import json
import sys

from app.config import settings


def cors_configuration(origins):
    if not origins:
        raise ValueError("KARMA_ALLOWED_ORIGINS is empty")
    return {
        "CORSRules": [
            {
                "AllowedOrigins": list(origins),
                "AllowedMethods": ["PUT", "GET"],
                "AllowedHeaders": ["Content-Type"],
                "MaxAgeSeconds": 600,
            }
        ]
    }


def main(argv):
    from app.services.storage import Storage

    cfg = settings()
    configuration = cors_configuration(cfg.karma_origins)
    print(json.dumps(configuration, indent=2))
    if "--apply" in argv:
        storage = Storage()
        if not storage.s3:
            raise SystemExit("Local storage serves CORS from the API; nothing to apply.")
        storage.s3.put_bucket_cors(Bucket=cfg.s3_bucket, CORSConfiguration=configuration)


if __name__ == "__main__":
    main(sys.argv[1:])
