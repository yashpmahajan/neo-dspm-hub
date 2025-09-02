from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, Form
from fastapi.responses import FileResponse
import json, csv, os
from fpdf import FPDF
from app.routes.user import get_current_user
import boto3
from app.db.mongodb import users_collection
from app.core import os as app_os

router = APIRouter()

DATA = [
    {"entity": "AGE", "value": "25"},
    {"entity": "AWS_PRESIGNED_URL", "value": "https://s3-us-west-2.amazonaws.com/scancloud-test-bucket/scancloud-test-file.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA3Z7%2Fs3%2Faws4_request&X-Amz-Date=AWS4-HMAC-SHA256&X-Amz-SignedHeaders=AWS4-HMAC-SHA256&X-Amz-Security-Token=AWS4-HMAC-SHA256&X-Amz-Signature=1234ab7890121234567890cd12345678901212345678ef121234567890121234"},
    {"entity": "AZURE_SAS_TOKEN_STRING", "value": "https://myaccount.blob.core.windows.net/mycontainer/myfile.txt?sv=2023-11-03&ss=b&srt=sco&sp=r&se=2025-05-20T00:00:00Z&st=2025-05-16T00:00:00Z&spr=https&sig=fakesignature1234567890"},
    {"entity": "BR_SUS_CARD_ID", "value": "898001710000000"},
    {"entity": "BUSINESS_TITLE", "value": "Account Director"},
    {"entity": "CARD_SECURITY_CODE", "value": "123"},
    {"entity": "CARD_SECURITY_CODE", "value": "345"},
    {"entity": "CARD_SECURITY_CODE", "value": "910"},
    {"entity": "CH_HEALTH_INSURANCE_CARD_NUMBER", "value": "80756014141414141414"},
    {"entity": "CREDIT_CARD_NUMBER", "value": "4111-1111-1111-1111"},
    {"entity": "CRYPTO", "value": "17NdbrSGoUotzeGCcMMCqnFkEvLymoou9j"},
    {"entity": "DATE", "value": "10-Jun-2024"},
    {"entity": "DOB", "value": "10-Jun-1994"},
    {"entity": "EMAIL_ADDRESS", "value": "mark_hill@proofpoint.com"},
    {"entity": "EU_PHONE_NUMBER", "value": "+49 151 23456789"},
    {"entity": "EU_PHONE_NUMBER", "value": "+39 347 123 4567"},
    {"entity": "EU_PHONE_NUMBER", "value": "+353 87 123 4567"},
    {"entity": "GENERAL_DEVICE_ID_OR_NAME", "value": "DESKTOP-99A7B6"},
    {"entity": "GENERAL_PATIENT_ID_OR_NAME", "value": "ZXCVBNM123456"},
    {"entity": "GENERAL_SERVICE_ACCOUNT", "value": "abcsadmin"},
    {"entity": "GENERAL_USER_ID_OR_NAME", "value": "EinsteinAlbert"},
    {"entity": "HASHED_PASSWORD", "value": "$2b$12$FagYHfhdESCIOAC176jbtesq665v.9WQr8/ZrHWzluq7Ry0wQOooO"},
    {"entity": "ICD_CODE", "value": "A2A.ABC"},
    {"entity": "IN_GSTIN", "value": "27AAPFU0939F1ZV"},
    {"entity": "IHG_REWARDS_NUMBER", "value": "123451111"},
    {"entity": "INCOME", "value": "$100000"},
    {"entity": "IP_ADDRESS", "value": "223.255.255.254"},
    {"entity": "JWT_AUTH_TOKEN", "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"},
    {"entity": "MAC_ADDRESS", "value": "00:1B:63:84:45:E6"},
    {"entity": "MARITAL_STATUS", "value": "Married"},
    {"entity": "PHONE_NUMBER", "value": "408-545-3343"},
    {"entity": "SWIFT_CODE", "value": "WFBIUS6S"},
    {"entity": "URL_ADDRESS", "value": "https://sub.domain.example.co.uk/path?query=value#anchor"},
    {"entity": "URL_ADDRESS", "value": "ftp://ftp.example.org/file.txt"},
    {"entity": "URL_ADDRESS", "value": "htp://example.com"},
    {"entity": "URL_ADDRESS", "value": "http:///example.com"},
    {"entity": "US_ATIN", "value": "912-93-0000"},
    {"entity": "US_BANK_NUMBER", "value": "12345678"},
    {"entity": "US_MEDICAL_INSURANCE_ID", "value": "R123456789"},
    {"entity": "US_SSN", "value": "713-11-1111"},
    {"entity": "UUID", "value": "123e4567-e89b-12d3-a456-426614174000"},
    {"entity": "VEHICLE_IDENTIFICATION_NUMBER", "value": "1G1YC12385B123458"}
]


SAVE_DIR = "app/generated_files"
os.makedirs(SAVE_DIR, exist_ok=True)

# Also persist the raw data as JSON in the artifacts directory with cleanup
ARTIFACTS_DIR = "artifacts"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

@router.get("/generatedata")
def generate_data(
    filetype: str = Query(..., enum=["json", "pdf", "csv"]),
    current_user: dict = Depends(get_current_user)
):
    # Clear existing files in SAVE_DIR
    for f in os.listdir(SAVE_DIR):
        file_path = os.path.join(SAVE_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # Cleanup previous artifacts/data.json if present
    artifact_json_path = os.path.join(ARTIFACTS_DIR, "data.json")
    if os.path.exists(artifact_json_path) and os.path.isfile(artifact_json_path):
        os.remove(artifact_json_path)

    filename = os.path.join(SAVE_DIR, f"data.{filetype}")
    media_type = "application/octet-stream"

    # Create file
    if filetype == "json":
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(DATA, f, indent=2, ensure_ascii=False)
        media_type = "application/json"
    elif filetype == "csv":
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["entity", "value"])
            writer.writeheader()
            writer.writerows(DATA)
        media_type = "text/csv"
    elif filetype == "pdf":
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(0, 10, txt="Generated Data", ln=1)
        pdf.ln(3)
        pdf.set_font("Arial", size=11)
        for entry in DATA:
            entity = entry.get("entity", "")
            value = entry.get("value", "")
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(0, 8, txt=f"{entity}", ln=1)
            pdf.set_font("Arial", size=11)
            # Use multi_cell for long values
            pdf.multi_cell(0, 8, txt=f"{value}")
            pdf.ln(2)
        pdf.output(filename)
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Always store a JSON copy of DATA into artifacts/data.json
    with open(artifact_json_path, "w", encoding="utf-8") as af:
        json.dump(DATA, af, indent=2, ensure_ascii=False)

    # Return file
    return FileResponse(filename, media_type=media_type, filename=os.path.basename(filename))
# Upload generated file to a new AWS S3 bucket with timestamp in name, then upload file in userID folder
from datetime import datetime


@router.post("/uploadtobucket")
def upload_to_bucket(
    current_user: dict = Depends(get_current_user)
):
    # Auto-detect filetype from available files
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

    # Get user id from DB
    user = users_collection.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found in DB.")
    user_id = str(user["_id"])

    # AWS credentials from ENV
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
        raise HTTPException(status_code=500, detail="AWS credentials not set in ENV.")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    # Create bucket name with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    bucket_name = f"neo-bucket-{timestamp}"

    # Create bucket
    try:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create bucket: {e}")

    # S3 key: userID/data.filetype
    s3_key = f"{user_id}/data.{filetype}"

    try:
        s3.upload_file(filename, bucket_name, s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to S3: {e}")

    file_url = f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    return {"msg": "File uploaded successfully", "bucket_name": bucket_name, "file_url": file_url}

# Delete an AWS S3 bucket by name
@router.delete("/deletebucket")
def delete_bucket(bucket_name: str = Query(...), current_user: dict = Depends(get_current_user)):
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
        raise HTTPException(status_code=500, detail="AWS credentials not set in ENV.")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    # First, delete all objects in the bucket
    try:
        # List objects in the bucket
        objects = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
        # Delete the bucket
        s3.delete_bucket(Bucket=bucket_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bucket: {e}")

    return {"msg": f"Bucket '{bucket_name}' deleted successfully."}