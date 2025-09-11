from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
import json, csv, os, subprocess, re
from fpdf import FPDF
from app.routes.user import get_current_user
import boto3
from app.db.mongodb import users_collection
from datetime import datetime

router = APIRouter()

SAVE_DIR = "app/generated_files"
os.makedirs(SAVE_DIR, exist_ok=True)
ARTIFACTS_DIR = "artifacts"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# Strict financial test card generation prompt
CARD_PROMPT = (
    "You are a data generation expert. Generate exactly 3 highly realistic, unique, and plausible personal information records in strict JSON array format. "
    "Each record must include the following fields:fullName, email, ssnNumber, drivingLicenseNumber, passportNumber, dateOfBirth, and address. "
    "Requirements for each field:\n"
    "- fullName: Use common, natural full names (first and last together, avoid placeholders or obviously fake names).\n"
    "- email: Use realistic formats and common domains (e.g., gmail.com, yahoo.com, outlook.com, live.com), but do not use real or existing addresses. Do not use 'test', 'example', or similar dummy values.\n"
    "- ssnNumber: Use the format NNN-NN-NNNN, but do NOT use obvious dummy values (e.g., 123-45-6789, 987-65-4321, or any sequential/repetitive numbers). Use plausible, random numbers that look authentic.\n"
    "- drivingLicenseNumber: Format as two uppercase state initials followed by 6 digits (e.g., 'CA548745'). Use valid US state abbreviations. Do not use obvious patterns or dummy numbers.\n"
    "- passportNumber: Format as one uppercase letter followed by 8 digits (e.g., 'Y32567891'). Do not use 'A12345678' or similar dummy values.\n"
    "- dateOfBirth: Use realistic dates in the format YYYY-MM-DD. Ensure ages are plausible for adults (e.g., 21-65 years old).\n"
    "- address: Use realistic US addresses, including street, city, state abbreviation, and zip code. Do not use obviously fake or placeholder addresses, and avoid using letter combinations like 'BDGFHJKLMNOPQRSTUVWXY' in addresses.\n"
    "\n"
    "Strict rules:\n"
    "- All data must look authentic and indistinguishable from real data, but must not correspond to any real individuals.\n"
    "- Do NOT use any dummy, sequential, or repetitive values (e.g., 123456, 1234, 12345678, 987654321, etc.).\n"
    "- Do NOT use any example, test, or placeholder values.\n"
    "- Do NOT include any comments, explanations, or extra information—output ONLY the JSON array.\n"
)

def clean_ollama_output(text: str) -> str:
    # Remove code fences if present
    text = re.sub(r"^```[a-zA-Z]*", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    # Remove inline comments if any
    text = re.sub(r"//.*", "", text)
    return text.strip()

def process_with_ollama_for_credit_cards():
    try:
        completed = subprocess.run(
            ["ollama", "run", "tarique_salat/dspm-ai-model:latest", CARD_PROMPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600
        )
        raw_output = completed.stdout.strip()
        print("Raw Ollama output:", raw_output)  # debug

        cleaned = clean_ollama_output(raw_output)

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
        except Exception as e:
            print("JSON parsing error:", e)

        # Fallback: wrap cleaned raw text in entity/value structure
        return [{"entity": "AI_OUTPUT", "value": cleaned}]

    except Exception as e:
        return [{"entity": "AI_ERROR", "value": str(e)}]

@router.get("/generatedata")
def generate_data(
    filetype: str = Query(..., enum=["json", "pdf", "csv"]),
    # current_user: dict = Depends(get_current_user)
):
    # Clear existing files in SAVE_DIR
    for f in os.listdir(SAVE_DIR):
        file_path = os.path.join(SAVE_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # Cleanup previous artifacts/data.json if present
    artifact_json_path = os.path.join(ARTIFACTS_DIR, "data.json")
    if os.path.exists(artifact_json_path):
        os.remove(artifact_json_path)

    # ----- INTEGRATE OLLAMA MODEL -----
    processed_data = process_with_ollama_for_credit_cards()

    # Normalize always to list of dicts
    if isinstance(processed_data, dict):
        processed_data = [processed_data]

    filename = os.path.join(SAVE_DIR, f"data.{filetype}")
    media_type = "application/octet-stream"

    if filetype == "json":
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        media_type = "application/json"

    elif filetype == "csv":
        fieldnames = ["fullName", "email", "ssnNumber", "drivingLicenseNumber", "passportNumber", "dateOfBirth", "address"]
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in processed_data:
                address = row.get("address", "")
                if isinstance(address, dict):
                    address = ", ".join(f"{k}: {v}" for k, v in address.items())
                writer.writerow({
                    "fullName": row.get("fullName", ""),
                    "email": row.get("email", ""),
                    "ssnNumber": row.get("ssnNumber", ""),
                    "drivingLicenseNumber": row.get("drivingLicenseNumber", ""),
                    "passportNumber": row.get("passportNumber", ""),
                    "dateOfBirth": row.get("dateOfBirth", ""),
                    "address": address,
                })
        media_type = "text/csv"

    elif filetype == "pdf":
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(0, 10, txt="Generated Personal Information Test Data", ln=1)
        pdf.ln(3)

        for idx, entry in enumerate(processed_data, start=1):
            pdf.set_font("Arial", style="B", size=12)
            pdf.cell(0, 8, txt=f"Entry {idx}", ln=1)
            pdf.set_font("Arial", size=11)
            for key in ["fullName", "email", "ssnNumber", "drivingLicenseNumber", "passportNumber", "dateOfBirth", "address"]:
                value = entry.get(key, "")
                if isinstance(value, dict):
                    value = ", ".join(f"{k}: {v}" for k, v in value.items())
                pdf.set_font("Arial", style="B", size=11)
                pdf.cell(40, 8, txt=f"{key}: ", ln=0)  # Added space after colon
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 8, txt=str(value))
            pdf.ln(3)

        pdf.output(filename)
        media_type = "application/pdf"

    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Save a JSON copy in artifacts/data.json
    with open(artifact_json_path, "w", encoding="utf-8") as af:
        json.dump(processed_data, af, indent=2, ensure_ascii=False)

    return FileResponse(filename, media_type=media_type, filename=os.path.basename(filename))


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