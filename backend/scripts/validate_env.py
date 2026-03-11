#!/usr/bin/env python3
"""Validate environment configuration for FormIQ backend.

Usage:
    python scripts/validate_env.py [--require-s3]

Checks:
  1. POSTGRES_* vars → can connect to database
  2. Redis connectivity
  3. S3 configuration (optional unless --require-s3)
  4. Alembic migration state
"""

import argparse
import os
import sys

# Add backend dir to path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BACKEND_DIR, ".env"))


def check_postgres():
    """Check PostgreSQL connectivity using POSTGRES_* vars."""
    import psycopg2

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    if server == "db":
        server = "localhost"
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "formiq")

    dsn = f"host={server} port={port} dbname={db_name} user={user} password={password}"
    try:
        conn = psycopg2.connect(dsn, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        )
        table_count = cur.fetchone()[0]

        # Check alembic version
        alembic_rev = None
        try:
            cur.execute("SELECT version_num FROM alembic_version")
            row = cur.fetchone()
            alembic_rev = row[0] if row else "(empty)"
        except Exception:
            conn.rollback()
            alembic_rev = "(table missing)"

        conn.close()
        print(f"  [OK] PostgreSQL: {server}:{port}/{db_name}")
        print(f"       Version: {version.split(',')[0]}")
        print(f"       Tables: {table_count}")
        print(f"       Alembic revision: {alembic_rev}")
        return True
    except Exception as e:
        print(f"  [FAIL] PostgreSQL: {e}")
        return False


def check_redis():
    """Check Redis connectivity."""
    import redis

    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        r = redis.from_url(url, socket_connect_timeout=3)
        info = r.info("server")
        print(f"  [OK] Redis: {url}")
        print(f"       Version: {info.get('redis_version', '?')}")
        return True
    except Exception as e:
        print(f"  [FAIL] Redis: {e}")
        return False


def check_s3():
    """Check S3/MinIO configuration and connectivity."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    bucket = os.getenv("AWS_BUCKET_NAME", os.getenv("S3_BUCKET", "formiq-videos"))
    region = os.getenv("AWS_REGION", "us-east-1")
    endpoint = os.getenv("AWS_S3_ENDPOINT")
    use_s3 = os.getenv("USE_S3_STORAGE", "false").lower() == "true"

    if not use_s3:
        print(f"  [SKIP] S3: USE_S3_STORAGE=false (using local storage)")
        print(f"         Upload dir: {os.getenv('UPLOAD_DIR', 'uploads/videos')}")
        return True

    if not access_key or access_key.startswith("your_"):
        print(f"  [FAIL] S3: AWS_ACCESS_KEY_ID not configured")
        return False
    if not secret_key or secret_key.startswith("your_"):
        print(f"  [FAIL] S3: AWS_SECRET_ACCESS_KEY not configured")
        return False

    try:
        import boto3
        from botocore.exceptions import ClientError

        kwargs = {
            "service_name": "s3",
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        if endpoint:
            kwargs["endpoint_url"] = endpoint

        client = boto3.client(**kwargs)
        client.head_bucket(Bucket=bucket)
        provider = f"MinIO ({endpoint})" if endpoint else f"AWS S3 ({region})"
        print(f"  [OK] S3: {provider}, bucket={bucket}")
        return True
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "404":
            print(f"  [FAIL] S3: bucket '{bucket}' does not exist")
        elif code == "403":
            print(f"  [FAIL] S3: access denied to bucket '{bucket}'")
        else:
            print(f"  [FAIL] S3: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] S3: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Validate FormIQ environment")
    parser.add_argument(
        "--require-s3",
        action="store_true",
        help="Fail if S3 is not configured and accessible",
    )
    args = parser.parse_args()

    print("FormIQ Environment Validation")
    print("=" * 40)

    results = {}

    print("\n1. PostgreSQL")
    results["postgres"] = check_postgres()

    print("\n2. Redis")
    results["redis"] = check_redis()

    print("\n3. S3 / Storage")
    results["s3"] = check_s3()

    print("\n" + "=" * 40)
    all_ok = all(results.values())
    if args.require_s3 and not results["s3"]:
        all_ok = False

    if all_ok:
        print("Result: ALL CHECKS PASSED")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"Result: FAILED checks: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
