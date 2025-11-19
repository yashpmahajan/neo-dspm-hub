from fastapi import APIRouter, HTTPException
import os

from app.utils import database_helper as dbh

router = APIRouter()

SAVE_DIR = "app/generated_files"


@router.post("/upload-env-bucket")
def upload_env_bucket():
    # Get AWS creds and bucket name from env
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
    # if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME]):
    #     raise HTTPException(status_code=500, detail="AWS credentials or bucket name not set in ENV.")

    # Find the first generated file
    filetype, filename = dbh.get_first_generated_file(SAVE_DIR)
    if not filetype or not filename:
        raise HTTPException(status_code=404, detail="No generated file found. Please generate the file first.")

    s3 = dbh.s3_create(
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        AWS_REGION,
    )

    # Clear all files in the bucket before uploading
    try:
        dbh.s3_clear_bucket(s3, AWS_BUCKET_NAME)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear bucket: {e}")

    s3_key = f"data.{filetype}"
    try:
        dbh.s3_upload_file(s3, AWS_BUCKET_NAME, filename, s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to S3: {e}")

    file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    return {"msg": "File uploaded successfully", "bucket_name": AWS_BUCKET_NAME, "file_url": file_url}


@router.post("/upload-blob-storage")
def upload_to_blob_storage():
    # Upload the first generated file (data.json|data.pdf|data.csv) to Azure Blob Storage
    # Uses env vars: AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY, AZURE_CONTAINER_NAME
    AZURE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    AZURE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

    # Find the first generated file
    filetype, filename = dbh.get_first_generated_file(SAVE_DIR)
    if not filetype or not filename:
        raise HTTPException(status_code=404, detail="No generated file found. Please generate the file first.")

    # Lazy import to avoid hard dependency at module import time
    try:
        from azure.storage.blob import BlobServiceClient
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure SDK not available: {e}")

    if not all([AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME]):
        raise HTTPException(status_code=500, detail="Azure storage credentials or container name not set in ENV.")

    try:
        account_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net"
        service_client = dbh.blob_service_client_create(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY)
        container_client = service_client.get_container_client(AZURE_CONTAINER_NAME)

        # Ensure container exists (will raise if account/container invalid)
        if not container_client.exists():
            # Try to create the container if it doesn't exist
            container_client.create_container()

        # Clear existing blobs in the container
        try:
            dbh.clear_container_blobs(container_client)
        except Exception:
            # If deletion fails, continue and attempt upload; bubble up if needed
            pass

        blob_name = f"data.{filetype}"
        dbh.upload_blob_from_file(container_client, blob_name, filename, overwrite=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to Azure Blob Storage: {e}")

    file_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}"
    return {"msg": "File uploaded successfully", "container_name": AZURE_CONTAINER_NAME, "file_url": file_url}


@router.post("/upload-aws-rds")
def upload_to_aws_rds(db_identifier: str = None):
    """
    Upload first generated JSON/CSV to an RDS Postgres DB. Endpoint discovery:
     - If RDS_HOST is set in env, use it.
     - Else if db_identifier provided (or RDS_DB_IDENTIFIER env), use AWS Describe calls (boto3).
    """
    # unchanged: find file
    SAVE_DIR = "app/generated_files"
    filetype = None
    filename = None
    for ext in ["json", "csv"]:
        test_path = os.path.join(SAVE_DIR, f"data.{ext}")
        if os.path.exists(test_path):
            filetype = ext
            filename = test_path
            break
    if not filetype or not filename:
        raise HTTPException(status_code=404, detail="No generated JSON/CSV file found. Please generate the file first.")

    # RDS connection config — prefer explicit env; else try discovery via AWS
    RDS_HOST = os.getenv("RDS_HOST")
    RDS_PORT = int(os.getenv("RDS_PORT", "5432"))
    RDS_DB_NAME = os.getenv("RDS_DB_NAME")
    RDS_USER = os.getenv("RDS_USER")
    RDS_PASSWORD = os.getenv("RDS_PASSWORD")

    # If host not present, attempt discovery via AWS
    if not RDS_HOST:
        # try db_identifier param, then env
        db_id = db_identifier or os.getenv("RDS_DB_IDENTIFIER")
        if not db_id:
            raise HTTPException(status_code=500, detail="RDS_HOST not set and RDS_DB_IDENTIFIER not provided for discovery.")
        # AWS creds: pass explicit if env present, otherwise boto3 will use role/profile
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_session = os.getenv("AWS_SESSION_TOKEN")
        aws_region = os.getenv("AWS_REGION") or "us-east-1"

        host, port = dbh.get_rds_endpoint_from_aws(
            db_identifier=db_id,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret,
            aws_session_token=aws_session,
            region_name=aws_region,
        )
        RDS_HOST = host
        RDS_PORT = port

    # Validate required DB creds
    if not all([RDS_HOST, RDS_DB_NAME, RDS_USER, RDS_PASSWORD]):
        raise HTTPException(status_code=500, detail="Missing DB connection details (RDS_HOST, RDS_DB_NAME, RDS_USER, RDS_PASSWORD).")

    # connect to Postgres using psycopg2 and then perform the same logic as before
    try:
        import psycopg2
        from psycopg2 import sql
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"psycopg2 required: {e}")

    conn = None
    previous_files = []
    previous_records = []
    try:
        conn = psycopg2.connect(host=RDS_HOST, port=RDS_PORT, dbname=RDS_DB_NAME, user=RDS_USER, password=RDS_PASSWORD)
        cur = conn.cursor()
        # (reuse your table creation, record insertion logic here)
        # --- create dspm_files table ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dspm_files (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                filetype TEXT NOT NULL,
                content BYTEA NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        # gather previous dspm_files rows
        try:
            cur.execute("SELECT id, filename, filetype, octet_length(content) AS size, created_at FROM dspm_files;")
            existing_rows = cur.fetchall()
        except Exception:
            existing_rows = []
        for r in existing_rows:
            _id, _fname, _ftype, _size, _created = r
            try:
                created_iso = _created.isoformat() if _created is not None else None
            except Exception:
                created_iso = str(_created)
            previous_files.append({
                "id": _id,
                "filename": _fname,
                "filetype": _ftype,
                "size_bytes": _size,
                "created_at": created_iso,
            })
        # Also check dspm_records table preview
        try:
            cur.execute("SELECT id, data, created_at FROM dspm_records LIMIT 50;")
            rec_rows = cur.fetchall()
        except Exception:
            rec_rows = []
        for r in rec_rows:
            _id, _data, _created = r
            try:
                created_iso = _created.isoformat() if _created is not None else None
            except Exception:
                created_iso = str(_created)
            try:
                data_text = str(_data)
                preview = data_text[:200] + ("..." if len(data_text) > 200 else "")
                size_bytes = len(data_text.encode("utf-8"))
            except Exception:
                preview = None
                size_bytes = None
            previous_records.append({
                "id": _id,
                "preview": preview,
                "size_bytes": size_bytes,
                "created_at": created_iso,
            })

        # delete old entries
        cur.execute("DELETE FROM dspm_files;")
        # Insert structured data based on file type (JSON/CSV)
        if filetype == "json":
            import json
            with open(filename, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")
            if isinstance(data, dict):
                records = [data]
            elif isinstance(data, list):
                records = data
            else:
                raise HTTPException(status_code=400, detail="JSON root must be object or array")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dspm_records (
                    id SERIAL PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("DELETE FROM dspm_records;")
            try:
                from psycopg2.extras import Json as PsycopgJson
            except Exception:
                PsycopgJson = None
            for rec in records:
                if PsycopgJson:
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (PsycopgJson(rec),))
                else:
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (json.dumps(rec),))
        elif filetype == "csv":
            import csv
            import json as _json
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                records = [r for r in reader]
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dspm_records (
                    id SERIAL PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("DELETE FROM dspm_records;")
            try:
                from psycopg2.extras import Json as PsycopgJson
            except Exception:
                PsycopgJson = None
            for rec in records:
                if PsycopgJson:
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (PsycopgJson(rec),))
                else:
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (_json.dumps(rec),))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type for structured upload.")

        conn.commit()
        cur.close()
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload to RDS: {e}")
    finally:
        if conn:
            conn.close()

    return {
        "msg": "File uploaded to RDS successfully",
        "table": "dspm_files",
        "filename": os.path.basename(filename),
        "previous_files": previous_files,
        "previous_records": previous_records,
    }