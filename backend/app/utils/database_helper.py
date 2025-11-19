# File: app/utils/database_helper.py
import os
import boto3

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


