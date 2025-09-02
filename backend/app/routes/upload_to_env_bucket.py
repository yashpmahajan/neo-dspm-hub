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
