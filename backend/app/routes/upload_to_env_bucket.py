from fastapi import APIRouter, HTTPException
import os
import boto3

def clear_bucket(s3, bucket_name):
    # Delete all objects in the bucket
    try:
        objects = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear bucket: {e}")


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
    filetype = None
    filename = None
    for ext in ["json", "pdf", "csv"]:
        test_path = os.path.join(SAVE_DIR, f"data.{ext}")
        if os.path.exists(test_path):
            filetype = ext
            filename = test_path
            break
    if not filetype or not filename:
        raise HTTPException(status_code=404, detail="No generated file found. Please generate the file first.")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    # Clear all files in the bucket before uploading
    clear_bucket(s3, AWS_BUCKET_NAME)

    s3_key = f"data.{filetype}"
    try:
        s3.upload_file(filename, AWS_BUCKET_NAME, s3_key)
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
    filetype = None
    filename = None
    for ext in ["json", "pdf", "csv"]:
        test_path = os.path.join(SAVE_DIR, f"data.{ext}")
        if os.path.exists(test_path):
            filetype = ext
            filename = test_path
            break
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
        service_client = BlobServiceClient(account_url=account_url, credential=AZURE_ACCOUNT_KEY)
        container_client = service_client.get_container_client(AZURE_CONTAINER_NAME)

        # Ensure container exists (will raise if account/container invalid)
        if not container_client.exists():
            # Try to create the container if it doesn't exist
            container_client.create_container()

        # Clear existing blobs in the container
        try:
            blobs = container_client.list_blobs()
            for blob in blobs:
                container_client.delete_blob(blob.name)
        except Exception:
            # If deletion fails, continue and attempt upload; bubble up if needed
            pass

        blob_name = f"data.{filetype}"
        with open(filename, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to Azure Blob Storage: {e}")

    file_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}"
    return {"msg": "File uploaded successfully", "container_name": AZURE_CONTAINER_NAME, "file_url": file_url}

@router.post("/upload-aws-rds")
def upload_to_aws_rds():
    """
    Upload the first generated file to an Amazon RDS (PostgreSQL) database table.

    Behavior:
    - Looks for the first generated file in `app/generated_files` (data.json|data.pdf|data.csv).
    - Connects to RDS using env vars: RDS_HOST, RDS_PORT, RDS_DB_NAME, RDS_USER, RDS_PASSWORD.
    - Ensures a table `dspm_files` exists, deletes any existing rows, then inserts the file as one row.

    Notes / assumptions:
    - Uses PostgreSQL via `psycopg2`. If you use a different engine (MySQL), this function should be adapted.
    - The file is stored as binary in the `content` column. JSON files are not parsed into rows here.
    """
    # Find the first generated file
    filetype = None
    filename = None
    for ext in ["json", "pdf", "csv"]:
        test_path = os.path.join(SAVE_DIR, f"data.{ext}")
        if os.path.exists(test_path):
            filetype = ext
            filename = test_path
            break
    if not filetype or not filename:
        raise HTTPException(status_code=404, detail="No generated file found. Please generate the file first.")

    # Lazy import psycopg2 to avoid hard dependency at module import time
    try:
        import psycopg2
        from psycopg2 import sql
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"psycopg2 not available: {e}")

    # Read RDS connection details from env
    RDS_HOST = os.getenv("RDS_HOST")
    RDS_PORT = int(os.getenv("RDS_PORT", "5432"))
    RDS_DB_NAME = os.getenv("RDS_DB_NAME")
    RDS_USER = os.getenv("RDS_USER")
    RDS_PASSWORD = os.getenv("RDS_PASSWORD")

    if not all([RDS_HOST, RDS_DB_NAME, RDS_USER, RDS_PASSWORD]):
        raise HTTPException(status_code=500, detail="RDS connection details not set in ENV.")

    conn = None
    try:
        conn = psycopg2.connect(host=RDS_HOST, port=RDS_PORT, dbname=RDS_DB_NAME, user=RDS_USER, password=RDS_PASSWORD)
        cur = conn.cursor()

        # Create table if not exists
        create_table_q = """
        CREATE TABLE IF NOT EXISTS dspm_files (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            filetype TEXT NOT NULL,
            content BYTEA NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        """
        cur.execute(create_table_q)

        # Fetch and print existing rows before deleting
        try:
            cur.execute("SELECT id, filename, filetype, octet_length(content) AS size, created_at FROM dspm_files;")
            existing_rows = cur.fetchall()
        except Exception:
            existing_rows = []

        previous_files = []
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

        # Also check for structured records in dspm_records (if present)
        try:
            cur.execute("SELECT id, data, created_at FROM dspm_records LIMIT 50;")
            rec_rows = cur.fetchall()
        except Exception:
            rec_rows = []

        previous_records = []
        for r in rec_rows:
            _id, _data, _created = r
            try:
                created_iso = _created.isoformat() if _created is not None else None
            except Exception:
                created_iso = str(_created)
            # Create a small preview of the JSON data (avoid returning full sensitive content)
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

        # Print to stdout/logs for debugging/visibility
        print("Existing dspm_files rows before delete:", previous_files)
        print("Existing dspm_records rows before delete (preview):", previous_records)

        # Remove previous data (delete all rows)
        cur.execute("DELETE FROM dspm_files;")

        # Read file and insert structured data depending on file type
        if filetype == "json":
            import json

            with open(filename, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")

            # Normalize to list of records
            if isinstance(data, dict):
                records = [data]
            elif isinstance(data, list):
                records = data
            else:
                raise HTTPException(status_code=400, detail="JSON root must be an object or an array of objects")

            # Create a JSONB-backed table for records
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS dspm_records (
                    id SERIAL PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
                """
            )

            # Clear previous structured records
            cur.execute("DELETE FROM dspm_records;")

            # Insert each record as JSONB
            try:
                from psycopg2.extras import Json as PsycopgJson
            except Exception:
                PsycopgJson = None

            for rec in records:
                if PsycopgJson:
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (PsycopgJson(rec),))
                else:
                    # Fallback: dump to string (shouldn't happen if psycopg2.extras is present)
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (json.dumps(rec),))

        elif filetype == "csv":
            import csv
            import json as _json

            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                records = [r for r in reader]

            # Create JSONB table and insert CSV rows as JSON objects
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS dspm_records (
                    id SERIAL PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
                """
            )

            cur.execute("DELETE FROM dspm_records;")

            try:
                from psycopg2.extras import Json as PsycopgJson
            except Exception:
                PsycopgJson = None

            for rec in records:
                # csv.DictReader returns strings; keep as-is
                if PsycopgJson:
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (PsycopgJson(rec),))
                else:
                    cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (_json.dumps(rec),))

        else:
            # For binary formats like PDF we don't parse structured data here
            raise HTTPException(status_code=400, detail="RDS structured upload supports only JSON or CSV files. For PDFs use blob storage endpoint.")

        conn.commit()
        cur.close()

    except HTTPException:
        # re-raise http exceptions
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
    