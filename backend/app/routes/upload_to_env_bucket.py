from fastapi import APIRouter, HTTPException
import os
import json

from app.utils import database_helper as dbh
from typing import Optional
from app.utils.logger_helper import get_logger, log_api_request, log_api_response, log_error, log_step, log_success, log_warning

logger = get_logger("upload_to_env_bucket")

router = APIRouter()

SAVE_DIR = "app/generated_files"


@router.post("/upload-env-bucket")
def upload_env_bucket():
    log_api_request(logger, "POST", "/upload-env-bucket")
    
    try:
        log_step(logger, "Retrieving AWS credentials from environment")
        # Get AWS creds and bucket name from env
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
        log_success(logger, "AWS credentials retrieved", region=AWS_REGION, bucket_name=AWS_BUCKET_NAME)

        # Find the first generated file
        log_step(logger, "Finding first generated file", save_dir=SAVE_DIR)
        filetype, filename = dbh.get_first_generated_file(SAVE_DIR)
        if not filetype or not filename:
            log_error(logger, FileNotFoundError("No generated file found"), "File detection")
            raise HTTPException(status_code=404, detail="No generated file found. Please generate the file first.")
        log_success(logger, "Generated file found", filetype=filetype, filename=filename)

        log_step(logger, "Creating S3 client", region=AWS_REGION)
        s3 = dbh.s3_create(
            AWS_ACCESS_KEY_ID,
            AWS_SECRET_ACCESS_KEY,
            AWS_REGION,
        )

        # Clear all files in the bucket before uploading
        log_step(logger, "Clearing existing files in bucket", bucket_name=AWS_BUCKET_NAME)
        try:
            dbh.s3_clear_bucket(s3, AWS_BUCKET_NAME)
            log_success(logger, "Bucket cleared successfully", bucket_name=AWS_BUCKET_NAME)
        except Exception as e:
            # If botocore is available and this is a ClientError AccessDenied,
            # make clearing non-fatal and continue to upload (will overwrite the key).
            try:
                from botocore.exceptions import ClientError
            except Exception:
                ClientError = None

            if ClientError and isinstance(e, ClientError):
                # Try to get the AWS error code
                try:
                    err_code = e.response.get("Error", {}).get("Code")
                except Exception:
                    err_code = None

                if err_code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "403"):
                    log_warning(logger, f"Access denied when clearing bucket {AWS_BUCKET_NAME}; skipping clear and continuing", error=str(e))
                else:
                    log_error(logger, e, f"Failed to clear bucket: {AWS_BUCKET_NAME}")
                    raise HTTPException(status_code=500, detail=f"Failed to clear bucket: {e}")
            else:
                # If it's not a botocore ClientError, re-raise as before
                log_error(logger, e, f"Failed to clear bucket: {AWS_BUCKET_NAME}")
                raise HTTPException(status_code=500, detail=f"Failed to clear bucket: {e}")

        s3_key = f"data.{filetype}"
        log_step(logger, "Uploading file to S3", bucket=AWS_BUCKET_NAME, s3_key=s3_key, filename=filename)
        try:
            dbh.s3_upload_file(s3, AWS_BUCKET_NAME, filename, s3_key)
            log_success(logger, "File uploaded to S3", bucket=AWS_BUCKET_NAME, s3_key=s3_key)
        except Exception as e:
            log_error(logger, e, f"Failed to upload file to S3: {AWS_BUCKET_NAME}/{s3_key}")
            raise HTTPException(status_code=500, detail=f"Failed to upload to S3: {e}")

        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        log_api_response(logger, "POST", "/upload-env-bucket", status_code=200, bucket_name=AWS_BUCKET_NAME)
        return {"msg": "File uploaded successfully", "bucket_name": AWS_BUCKET_NAME, "file_url": file_url}
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During upload to env bucket")
        raise HTTPException(status_code=500, detail=f"Failed to upload to bucket: {str(e)}")


@router.post("/upload-blob-storage")
def upload_to_blob_storage():
    log_api_request(logger, "POST", "/upload-blob-storage")
    
    try:
        log_step(logger, "Retrieving Azure storage credentials from environment")
        # Upload the first generated file (data.json|data.pdf|data.csv) to Azure Blob Storage
        # Uses env vars: AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY, AZURE_CONTAINER_NAME
        AZURE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        AZURE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

        # Find the first generated file
        log_step(logger, "Finding first generated file", save_dir=SAVE_DIR)
        filetype, filename = dbh.get_first_generated_file(SAVE_DIR)
        if not filetype or not filename:
            log_error(logger, FileNotFoundError("No generated file found"), "File detection")
            raise HTTPException(status_code=404, detail="No generated file found. Please generate the file first.")
        log_success(logger, "Generated file found", filetype=filetype, filename=filename)

        # Lazy import to avoid hard dependency at module import time
        log_step(logger, "Importing Azure Blob Storage SDK")
        try:
            from azure.storage.blob import BlobServiceClient
        except Exception as e:
            log_error(logger, e, "Azure SDK import failed")
            raise HTTPException(status_code=500, detail=f"Azure SDK not available: {e}")

        if not all([AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME]):
            log_error(logger, ValueError("Azure credentials not set"), "Environment variable check")
            raise HTTPException(status_code=500, detail="Azure storage credentials or container name not set in ENV.")
        log_success(logger, "Azure credentials retrieved", account_name=AZURE_ACCOUNT_NAME, container_name=AZURE_CONTAINER_NAME)

        try:
            log_step(logger, "Creating Azure Blob Service Client", account_name=AZURE_ACCOUNT_NAME)
            account_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net"
            service_client = dbh.blob_service_client_create(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY)
            container_client = service_client.get_container_client(AZURE_CONTAINER_NAME)

            # Ensure container exists (will raise if account/container invalid)
            log_step(logger, "Checking if container exists", container_name=AZURE_CONTAINER_NAME)
            if not container_client.exists():
                log_step(logger, "Container does not exist, creating it", container_name=AZURE_CONTAINER_NAME)
                # Try to create the container if it doesn't exist
                container_client.create_container()
                log_success(logger, "Container created", container_name=AZURE_CONTAINER_NAME)
            else:
                log_success(logger, "Container exists", container_name=AZURE_CONTAINER_NAME)

            # Clear existing blobs in the container
            log_step(logger, "Clearing existing blobs in container", container_name=AZURE_CONTAINER_NAME)
            try:
                dbh.clear_container_blobs(container_client)
                log_success(logger, "Container blobs cleared", container_name=AZURE_CONTAINER_NAME)
            except Exception as e:
                log_warning(logger, f"Failed to clear container blobs: {e}", continuing="upload")
                # If deletion fails, continue and attempt upload; bubble up if needed
                pass

            blob_name = f"data.{filetype}"
            log_step(logger, "Uploading file to Azure Blob Storage", blob_name=blob_name, filename=filename)
            dbh.upload_blob_from_file(container_client, blob_name, filename, overwrite=True)
            log_success(logger, "File uploaded to Azure Blob Storage", blob_name=blob_name, container=AZURE_CONTAINER_NAME)

        except HTTPException:
            raise
        except Exception as e:
            log_error(logger, e, "During Azure Blob Storage upload")
            raise HTTPException(status_code=500, detail=f"Failed to upload to Azure Blob Storage: {e}")

        file_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}"
        log_api_response(logger, "POST", "/upload-blob-storage", status_code=200, container_name=AZURE_CONTAINER_NAME)
        return {"msg": "File uploaded successfully", "container_name": AZURE_CONTAINER_NAME, "file_url": file_url}
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During blob storage upload")
        raise HTTPException(status_code=500, detail=f"Failed to upload to blob storage: {str(e)}")


@router.post("/upload-aws-rds")
def upload_to_aws_rds(db_identifier: str = None):
    """
    Upload first generated JSON/CSV to an RDS Postgres DB. Endpoint discovery:
     - If RDS_HOST is set in env, use it.
     - Else if db_identifier provided (or RDS_DB_IDENTIFIER env), use AWS Describe calls (boto3).
    """
    log_api_request(logger, "POST", "/upload-aws-rds", db_identifier=db_identifier)
    
    try:
        log_step(logger, "Finding generated JSON/CSV file")
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
            log_error(logger, FileNotFoundError("No generated file found"), "File detection")
            raise HTTPException(status_code=404, detail="No generated JSON/CSV file found. Please generate the file first.")
        log_success(logger, "Generated file found", filetype=filetype, filename=filename)

        # RDS connection config — prefer explicit env; else try discovery via AWS
        log_step(logger, "Retrieving RDS connection configuration from environment")
        RDS_HOST = os.getenv("RDS_HOST")
        RDS_PORT = int(os.getenv("RDS_PORT", "5432"))
        RDS_DB_NAME = os.getenv("RDS_DB_NAME")
        RDS_USER = os.getenv("RDS_USER")
        RDS_PASSWORD = os.getenv("RDS_PASSWORD")

        # If host not present, attempt discovery via AWS
        if not RDS_HOST:
            log_step(logger, "RDS_HOST not set, attempting AWS discovery", db_identifier=db_identifier)
            # try db_identifier param, then env
            db_id = db_identifier or os.getenv("RDS_DB_IDENTIFIER")
            if not db_id:
                log_error(logger, ValueError("RDS_DB_IDENTIFIER not provided"), "RDS endpoint discovery")
                raise HTTPException(status_code=500, detail="RDS_HOST not set and RDS_DB_IDENTIFIER not provided for discovery.")
            # AWS creds: pass explicit if env present, otherwise boto3 will use role/profile
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session = os.getenv("AWS_SESSION_TOKEN")
            aws_region = os.getenv("AWS_REGION") or "us-east-1"

            log_step(logger, "Discovering RDS endpoint from AWS", db_identifier=db_id, region=aws_region)
            host, port = dbh.get_rds_endpoint_from_aws(
                db_identifier=db_id,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret,
                aws_session_token=aws_session,
                region_name=aws_region,
            )
            RDS_HOST = host
            RDS_PORT = port
            log_success(logger, "RDS endpoint discovered", host=RDS_HOST, port=RDS_PORT)
        else:
            log_success(logger, "Using RDS_HOST from environment", host=RDS_HOST, port=RDS_PORT)

        # Validate required DB creds
        log_step(logger, "Validating RDS connection credentials")
        if not all([RDS_HOST, RDS_DB_NAME, RDS_USER, RDS_PASSWORD]):
            log_error(logger, ValueError("Missing DB connection details"), "Credential validation")
            raise HTTPException(status_code=500, detail="Missing DB connection details (RDS_HOST, RDS_DB_NAME, RDS_USER, RDS_PASSWORD).")

        # connect to Postgres using psycopg2 and then perform the same logic as before
        log_step(logger, "Importing psycopg2 library")
        try:
            import psycopg2
            from psycopg2 import sql
        except Exception as e:
            log_error(logger, e, "psycopg2 import failed")
            raise HTTPException(status_code=500, detail=f"psycopg2 required: {e}")

        conn = None
        previous_files = []
        previous_records = []
        try:
            log_step(logger, "Connecting to RDS Postgres database", host=RDS_HOST, port=RDS_PORT, database=RDS_DB_NAME)
            conn = psycopg2.connect(host=RDS_HOST, port=RDS_PORT, dbname=RDS_DB_NAME, user=RDS_USER, password=RDS_PASSWORD)
            cur = conn.cursor()
            log_success(logger, "Connected to RDS database", host=RDS_HOST, database=RDS_DB_NAME)
            # (reuse your table creation, record insertion logic here)
            # --- create dspm_files table ---
            log_step(logger, "Creating dspm_files table if not exists")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dspm_files (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    filetype TEXT NOT NULL,
                    content BYTEA NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            log_success(logger, "dspm_files table ready")
            # gather previous dspm_files rows
            log_step(logger, "Fetching previous dspm_files records")
            try:
                cur.execute("SELECT id, filename, filetype, octet_length(content) AS size, created_at FROM dspm_files;")
                existing_rows = cur.fetchall()
                log_success(logger, f"Found {len(existing_rows)} previous file record(s)")
            except Exception as e:
                log_warning(logger, f"Could not fetch previous files: {e}", continuing="upload")
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
            log_step(logger, "Deleting old entries from dspm_files table")
            cur.execute("DELETE FROM dspm_files;")
            
            # Insert structured data based on file type (JSON/CSV)
            log_step(logger, f"Processing {filetype} file for upload", filename=filename)
            if filetype == "json":
                import json
                with open(filename, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception as e:
                        log_error(logger, e, "JSON file parsing failed")
                        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")
                if isinstance(data, dict):
                    records = [data]
                elif isinstance(data, list):
                    records = data
                else:
                    log_error(logger, ValueError("Invalid JSON structure"), "JSON validation")
                    raise HTTPException(status_code=400, detail="JSON root must be object or array")
                log_success(logger, f"Parsed JSON file", records=len(records))
                
                log_step(logger, "Creating dspm_records table if not exists")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS dspm_records (
                        id SERIAL PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                """)
                log_step(logger, "Deleting old records from dspm_records table")
                cur.execute("DELETE FROM dspm_records;")
                try:
                    from psycopg2.extras import Json as PsycopgJson
                except Exception:
                    PsycopgJson = None
                log_step(logger, f"Inserting {len(records)} record(s) into dspm_records")
                for rec in records:
                    if PsycopgJson:
                        cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (PsycopgJson(rec),))
                    else:
                        cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (json.dumps(rec),))
                log_success(logger, f"Inserted {len(records)} record(s) into dspm_records")
            elif filetype == "csv":
                log_step(logger, "Reading and parsing CSV file")
                import csv
                import json as _json
                with open(filename, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    records = [r for r in reader]
                log_success(logger, f"Parsed CSV file", records=len(records))
                
                log_step(logger, "Creating dspm_records table if not exists")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS dspm_records (
                        id SERIAL PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT now()
                    );
                """)
                log_step(logger, "Deleting old records from dspm_records table")
                cur.execute("DELETE FROM dspm_records;")
                try:
                    from psycopg2.extras import Json as PsycopgJson
                except Exception:
                    PsycopgJson = None
                log_step(logger, f"Inserting {len(records)} record(s) into dspm_records")
                for rec in records:
                    if PsycopgJson:
                        cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (PsycopgJson(rec),))
                    else:
                        cur.execute("INSERT INTO dspm_records (data) VALUES (%s);", (_json.dumps(rec),))
                log_success(logger, f"Inserted {len(records)} record(s) into dspm_records")
            else:
                log_error(logger, ValueError(f"Unsupported file type: {filetype}"), "File type validation")
                raise HTTPException(status_code=400, detail="Unsupported file type for structured upload.")

            log_step(logger, "Committing transaction")
            conn.commit()
            cur.close()
            log_success(logger, "Transaction committed successfully")
        except HTTPException:
            if conn:
                log_step(logger, "Rolling back transaction due to HTTPException")
                conn.rollback()
            raise
        except Exception as e:
            if conn:
                log_error(logger, e, "Rolling back transaction due to error")
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to upload to RDS: {e}")
        finally:
            if conn:
                log_step(logger, "Closing database connection")
                conn.close()

        log_api_response(logger, "POST", "/upload-aws-rds", status_code=200, filename=os.path.basename(filename), records=len(previous_records))
        return {
            "msg": "File uploaded to RDS successfully",
            "table": "dspm_files",
            "filename": os.path.basename(filename),
            "previous_files": previous_files,
            "previous_records": previous_records,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During RDS upload")
        raise HTTPException(status_code=500, detail=f"Failed to upload to RDS: {str(e)}")
    
    
@router.post("/upload-azure-sql")
def upload_to_azure_sql(server_name: Optional[str] = None,
                       resource_group: Optional[str] = None,
                       subscription_id: Optional[str] = None):
    """
    Read JSON from app/artifacts/data.json and store each entry (or the single object)
    into dspm_records.data in Azure SQL.
    """
    log_api_request(logger, "POST", "/upload-azure-sql", server_name=server_name, resource_group=resource_group, subscription_id=subscription_id)
    
    try:
        log_step(logger, "Locating data.json file in artifacts directory")
        # Use absolute path for backend/artifacts/data.json
        test_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "data.json"))
        filetype = None
        filename = None

        # ensure file exists
        if os.path.exists(test_path):
            filetype = "json"
            filename = test_path
            log_success(logger, "Found data.json file", path=test_path)
        else:
            log_error(logger, FileNotFoundError("data.json not found"), f"File path: {test_path}")
            raise HTTPException(status_code=404, detail=f"No data.json found at {test_path}. Place your JSON at this path and retry.")

        # Connection details (env)
        log_step(logger, "Retrieving Azure SQL connection configuration from environment")
        AZURE_SQL_PORT = int(os.getenv("AZURE_SQL_PORT", "1433"))
        AZURE_SQL_DB = os.getenv("AZURE_SQL_DB")
        AZURE_SQL_USER = os.getenv("AZURE_SQL_USER")        # e.g., "user@servername" or "dspm"
        AZURE_SQL_PASSWORD = os.getenv("AZURE_SQL_PASSWORD")

        # Attempt discovery if host missing — prefer explicit query params, then env vars
        subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = resource_group or os.getenv("AZURE_RESOURCE_GROUP")
        server_name = server_name or os.getenv("AZURE_SQL_SERVER_NAME")

        log_step(logger, "Azure SQL discovery parameters", subscription_id=subscription_id, resource_group=resource_group, server_name=server_name)

        if not all([subscription_id, resource_group, server_name]):
            log_error(logger, ValueError("Missing discovery parameters"), "Azure SQL host discovery")
            raise HTTPException(status_code=500, detail="AZURE_SQL_HOST not set and subscription_id/resource_group/server_name not provided for discovery.")

        log_step(logger, "Discovering Azure SQL host endpoint")
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")
        AZURE_SQL_HOST, AZURE_SQL_PORT = dbh.discover_azure_sql_host(
            subscription_id=subscription_id,
            resource_group=resource_group,
            server_name=server_name,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        log_success(logger, "Azure SQL host discovered", host=AZURE_SQL_HOST, port=AZURE_SQL_PORT)

        if not all([AZURE_SQL_HOST, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD]):
            log_error(logger, ValueError("Missing DB connection details"), "Credential validation")
            raise HTTPException(status_code=500, detail="Missing DB connection details. Set AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD and either AZURE_SQL_HOST or provide subscription/resource_group/server_name for discovery.")

        # connect using pyodbc
        log_step(logger, "Importing pyodbc library")
        try:
            import pyodbc
            log_success(logger, "pyodbc imported successfully", available_drivers=len(pyodbc.drivers()))
        except Exception as e:
            log_error(logger, e, "pyodbc import failed")
            raise HTTPException(status_code=500, detail=f"pyodbc required: {e}")

        conn = None
        previous_records = []
        inserted_count = 0
        inserted_preview = []

        try:
            # choose ODBC driver (prefer modern MS drivers)
            log_step(logger, "Selecting ODBC driver")
            available_drivers = pyodbc.drivers()
            preferred_order = [
                "ODBC Driver 18 for SQL Server",
                "ODBC Driver 17 for SQL Server",
                "SQL Server",
            ]
            driver = None
            for name in preferred_order:
                if name in available_drivers:
                    driver = name
                    break
            if not driver:
                log_error(logger, ValueError("No suitable ODBC driver found"), f"Available drivers: {available_drivers}")
                raise HTTPException(status_code=500, detail=f"No SQL Server ODBC driver found. Available drivers: {available_drivers}")

            log_success(logger, "ODBC driver selected", driver=driver)

            log_step(logger, "Building connection string", host=AZURE_SQL_HOST, port=AZURE_SQL_PORT, database=AZURE_SQL_DB)
            conn_str = (
                "DRIVER={{{driver}}};"
                "SERVER={server},{port};"
                "DATABASE={db};"
                "UID={user};"
                "PWD={pwd};"
                "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;"
            ).format(
                driver=driver,
                server=AZURE_SQL_HOST,
                port=AZURE_SQL_PORT,
                db=AZURE_SQL_DB,
                user=AZURE_SQL_USER,
                pwd=AZURE_SQL_PASSWORD,
            )

            log_step(logger, "Connecting to Azure SQL database", host=AZURE_SQL_HOST, database=AZURE_SQL_DB)
            conn = pyodbc.connect(conn_str, autocommit=False)
            cur = conn.cursor()
            log_success(logger, "Connected to Azure SQL database", host=AZURE_SQL_HOST, database=AZURE_SQL_DB)

            # Ensure dspm_files table exists (kept for compatibility)
            log_step(logger, "Creating dspm_files table if not exists")
            cur.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dspm_files')
            BEGIN
                CREATE TABLE dspm_files (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    filename NVARCHAR(512) NOT NULL,
                    filetype NVARCHAR(50) NOT NULL,
                    content VARBINARY(MAX) NOT NULL,
                    created_at DATETIMEOFFSET DEFAULT SYSUTCDATETIME()
                );
            END
            """)
            log_success(logger, "dspm_files table ready")



            # 1. Ensure dspm_records table exists before fetching previous records
            log_step(logger, "Creating dspm_records table if not exists")
            cur.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dspm_records')
            BEGIN
                CREATE TABLE dspm_records (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    data NVARCHAR(MAX) NOT NULL,
                    created_at DATETIMEOFFSET DEFAULT SYSUTCDATETIME()
                );
            END
            """)
            log_success(logger, "dspm_records table ready")

            # 2. Get previous records (before deletion)
            log_step(logger, "Fetching previous dspm_records (top 50)")
            previous_records = []
            try:
                cur.execute("SELECT TOP 50 id, LEFT(CAST(data AS NVARCHAR(MAX)), 200) as preview, DATALENGTH(CAST(data AS NVARCHAR(MAX))) AS size_bytes, CONVERT(VARCHAR(33), created_at, 127) as created_at FROM dspm_records;")
                rec_rows = cur.fetchall()
                log_success(logger, f"Found {len(rec_rows)} previous record(s)")
            except Exception as e:
                log_warning(logger, f"Could not fetch previous records: {e}", continuing="upload")
                rec_rows = []

            for r in rec_rows:
                try:
                    _id = int(r[0])
                    preview = r[1] if len(r) > 1 else None
                    size_bytes = int(r[2]) if len(r) > 2 and r[2] is not None else None
                    created = r[3] if len(r) > 3 else None
                    try:
                        created_iso = created.isoformat() if created is not None else None
                    except Exception:
                        created_iso = str(created)
                except Exception:
                    _id = None
                    preview = None
                    size_bytes = None
                    created_iso = None
                previous_records.append({
                    "id": _id,
                    "preview": preview,
                    "size_bytes": size_bytes,
                    "created_at": created_iso,
                })

            # 3. Delete all records
            log_step(logger, "Deleting old records from dspm_records table")
            cur.execute("DELETE FROM dspm_records;")

            # 3. Upload new data
            if filetype == "json":
                log_step(logger, "Reading and parsing JSON file", filename=filename)
                with open(filename, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception as e:
                        log_error(logger, e, "JSON file parsing failed")
                        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")
                if isinstance(data, dict):
                    records = [data]
                elif isinstance(data, list):
                    records = data
                else:
                    log_error(logger, ValueError("Invalid JSON structure"), "JSON validation")
                    raise HTTPException(status_code=400, detail="JSON root must be an object or an array of objects")
                log_success(logger, f"Parsed JSON file", records=len(records))

                log_step(logger, f"Inserting {len(records)} record(s) into dspm_records")
                inserted_count = 0
                inserted_preview = []
                for rec in records:
                    json_text = json.dumps(rec, ensure_ascii=False)
                    cur.execute("INSERT INTO dspm_records (data) VALUES (?)", json_text)
                    inserted_count += 1
                    if len(inserted_preview) < 3:
                        inserted_preview.append(rec)
                log_success(logger, f"Inserted {inserted_count} record(s) into dspm_records")
            else:
                log_error(logger, ValueError(f"Unsupported file type: {filetype}"), "File type validation")
                raise HTTPException(status_code=400, detail="Unsupported file type for structured upload.")

            log_step(logger, "Committing transaction")
            conn.commit()
            cur.close()
            log_success(logger, "Transaction committed successfully")

        except HTTPException:
            if conn:
                log_step(logger, "Rolling back transaction due to HTTPException")
                conn.rollback()
            raise
        except Exception as e:
            if conn:
                log_error(logger, e, "Rolling back transaction due to error")
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to upload to Azure SQL: {e}")
        finally:
            if conn:
                log_step(logger, "Closing database connection")
                conn.close()

        log_api_response(logger, "POST", "/upload-azure-sql", status_code=200, filename=os.path.basename(filename), inserted_count=inserted_count)
        return {
            "msg": "File uploaded to Azure SQL successfully",
            "table": "dspm_records",
            "filename": os.path.basename(filename),
            "inserted_count": inserted_count,
            "inserted_preview": inserted_preview,
            "previous_records": previous_records,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During Azure SQL upload")
        raise HTTPException(status_code=500, detail=f"Failed to upload to Azure SQL: {str(e)}")