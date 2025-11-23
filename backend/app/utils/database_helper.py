# File: app/utils/database_helper.py
from http.client import HTTPException
import os
import boto3
from typing import Optional, Tuple

SAVE_DIR = os.path.join("app", "generated_files")


def get_first_generated_file(save_dir: str = SAVE_DIR):
    filetype = None
    filename = None
    for ext in ["json", "pdf", "csv"]:
        test_path = os.path.join(save_dir, f"data.{ext}")
        if os.path.exists(test_path):
            filetype = ext
            filename = test_path
            break
    return filetype, filename

def s3_create(aws_access_key_id, aws_secret_access_key, region_name="us-east-1"):
    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )


def s3_clear_bucket(s3_client, bucket_name):
    try:
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        if "Contents" in objects:
            for obj in objects["Contents"]:
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
    except Exception:
        raise


def s3_upload_file(s3_client, bucket_name, filename, s3_key):
    try:
        s3_client.upload_file(filename, bucket_name, s3_key)
    except Exception:
        raise


def blob_service_client_create(account_name: str, account_key: str):
    try:
        from azure.storage.blob import BlobServiceClient
    except Exception:
        raise
    account_url = f"https://{account_name}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=account_key)
    return service_client


def clear_container_blobs(container_client):
    blobs = container_client.list_blobs()
    for blob in blobs:
        container_client.delete_blob(blob.name)


def upload_blob_from_file(container_client, blob_name: str, filename: str, overwrite: bool = True):
    with open(filename, "rb") as data:
        container_client.upload_blob(name=blob_name, data=data, overwrite=overwrite)


def get_rds_endpoint_from_aws(db_identifier: str,
                              aws_access_key_id: str = None,
                              aws_secret_access_key: str = None,
                              aws_session_token: str = None,
                              region_name: str = None,
                              timeout_seconds: int = 10):
    """
    Return (host, port) for the given DB instance identifier by calling AWS RDS.
    Raises HTTPException on error.
    """
    try:
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"boto3 required for RDS discovery: {e}")

    # region fallback: use provided or env or default to us-east-1
    region = region_name or os.getenv("AWS_REGION") or "us-east-1"

    # Create client using explicit creds if provided, otherwise boto3 uses env/profile/role
    try:
        client = boto3.client(
            "rds",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region,
            config=Config(connect_timeout=timeout_seconds, read_timeout=timeout_seconds),
        )
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to create boto3 RDS client: {e}")

    # Try describe_db_instances first (covers non-Aurora and single-instance Aurora)
    try:
        resp = client.describe_db_instances(DBInstanceIdentifier=db_identifier)
        instances = resp.get("DBInstances", [])
        if not instances:
            raise HTTPException(status_code=404, detail=f"No DBInstances found for identifier: {db_identifier}")
        endpoint = instances[0].get("Endpoint")
        if endpoint and endpoint.get("Address"):
            return endpoint["Address"], int(endpoint.get("Port", 5432))
    except ClientError as e:
        # If not found or not permitted, we'll try describe_db_clusters fallback
        err_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        if err_code not in ("DBInstanceNotFound",):
            # if permission denied or other errors, raise
            if err_code == "AccessDenied":
                raise HTTPException(status_code=403, detail=f"AWS access denied for DescribeDBInstances: {e}")
            # else continue to try clusters
    except Exception as e:
        # proceed to try clusters as fallback
        pass

    # Fallback: describe DB clusters (Aurora)
    try:
        resp = client.describe_db_clusters(DBClusterIdentifier=db_identifier)
        clusters = resp.get("DBClusters", [])
        if clusters:
            # prefer Endpoint if present, else ReaderEndpoint
            cluster = clusters[0]
            endpoint_addr = cluster.get("Endpoint") or cluster.get("ReaderEndpoint")
            port = cluster.get("Port", 3306)  # default guess: depends on engine
            if endpoint_addr:
                return endpoint_addr, int(port)
    except ClientError as e:
        # If cluster not found, rethrow a clearer message
        err_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        if err_code == "DBClusterNotFoundFault":
            raise HTTPException(status_code=404, detail=f"No RDS instance or cluster found with identifier: {db_identifier}")
        else:
            raise HTTPException(status_code=500, detail=f"Error describing DB clusters: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error discovering RDS endpoint: {e}")

    raise HTTPException(status_code=404, detail=f"Could not discover endpoint for identifier: {db_identifier}")


def discover_azure_sql_host(subscription_id: str,
                            resource_group: str,
                            server_name: str,
                            tenant_id: Optional[str] = None,
                            client_id: Optional[str] = None,
                            client_secret: Optional[str] = None) -> Tuple[str, int]:
    """
    Discover Azure SQL server FQDN and port (1433).
    Uses ClientSecretCredential if tenant_id+client_id+client_secret provided,
    otherwise falls back to DefaultAzureCredential.
    Raises HTTPException on failure.
    """
    try:
        print("discover_azure_sql_host")
        print("DEBUG AUTH:",
              "tenant_id=", tenant_id,
              "client_id=", client_id,
              "client_secret_len=", len(client_secret) if client_secret else None)

        if tenant_id and client_id and client_secret:
            from azure.identity import ClientSecretCredential
            credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
        else:
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
        from azure.mgmt.sql import SqlManagementClient
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure SDK packages required (azure-identity, azure-mgmt-sql): {e}")

    try:
        client = SqlManagementClient(credential=credential, subscription_id=subscription_id)
        srv = client.servers.get(resource_group_name=resource_group, server_name=server_name)
        # preferred property name
        fqdn = getattr(srv, "fully_qualified_domain_name", None) or getattr(srv, "fullyQualifiedDomainName", None)
        if not fqdn:
            # fallback guess
            fqdn = f"{server_name}.database.windows.net"
        return fqdn, 1433
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover Azure SQL host: {e}")

