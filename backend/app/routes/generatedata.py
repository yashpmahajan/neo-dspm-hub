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
    {"name": "John Smith", "email": "john.smith@email.com", "phone": "(555) 123-4567", "ssn": "***-**-1234"},
    {"name": "Jane Doe", "email": "jane.doe@email.com", "phone": "(555) 987-6543", "ssn": "***-**-5678"},
    {"name": "Bob Johnson", "email": "bob.johnson@email.com", "phone": "(555) 456-7890", "ssn": "***-**-9012"}
]

SAVE_DIR = "app/generated_files"
os.makedirs(SAVE_DIR, exist_ok=True)


@router.get("/generatedata")
def generate_data(
    filetype: str = Query(..., enum=["json", "pdf", "csv"]),
    current_user: dict = Depends(get_current_user)
):
    filename = os.path.join(SAVE_DIR, f"data.{filetype}")
    # Create file
    if filetype == "json":
        with open(filename, "w") as f:
            json.dump(DATA, f, indent=2)
    elif filetype == "csv":
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DATA[0].keys())
            writer.writeheader()
            writer.writerows(DATA)
    elif filetype == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for entry in DATA:
            pdf.cell(200, 10, txt=f"Name: {entry['name']}", ln=1)
            pdf.cell(200, 10, txt=f"Email: {entry['email']}", ln=1)
            pdf.cell(200, 10, txt=f"Phone: {entry['phone']}", ln=1)
            pdf.cell(200, 10, txt=f"SSN: {entry['ssn']}", ln=1)
            pdf.cell(200, 10, txt="", ln=1)
        pdf.output(filename)
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")
    # Return file
    return FileResponse(filename, media_type="application/octet-stream", filename=os.path.basename(filename))
    
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
