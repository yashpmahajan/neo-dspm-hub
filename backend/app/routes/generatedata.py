from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
import json, csv, os, subprocess, re
from fpdf import FPDF
from app.routes.user import get_current_user
import boto3
from app.db.mongodb import users_collection
from datetime import datetime
from app.utils.logger_helper import (
    get_logger,
    log_api_request,
    log_api_response,
    log_error,
    log_step,
    log_success,
    log_warning,
)

logger = get_logger("generatedata")

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

HR_RECORD_PROMPT = (
      "You are an expert in generating realistic, professional, and confidential business documents for enterprise "
    "testing, security, compliance, and data-classification purposes.\n"
    "\n"
    "TASK:\n"
    "Generate a detailed, believable corporate document in plain text only. The document must look like it came from "
    "internal company systems and include realistic sensitive data such as:\n"
    "- Personal Identifiable Information (PII)\n"
    "- Employee details: name, employee ID, corporate email, personal email, masked phone number\n"
    "- Payroll and financial data: salary, masked bank accounts, routing numbers, IFSC/SWIFT codes\n"
    "- Internal system access: service accounts, device IDs, workstation IDs, synthetic JWT tokens\n"
    "- Government-issued IDs: synthetic PAN, SSN, Passport (partially masked)\n"
    "- Medical or HR-related synthetic information\n"
    "- Vendor or client details (if applicable)\n"
    "- Internal notes, compliance remarks, or HR observations\n"
    "\n"
    "DOCUMENT FORMAT:\n"
    "- Use headings, spacing, and sections similar to internal corporate files.\n"
    "- Include subheadings such as:\n"
    "  Employee Information\n"
    "  Payroll Data\n"
    "  Medical Insurance\n"
    "  IT Systems Access\n"
    "  Notes\n"
    "- Output must be plain text only. No JSON, no tables, no code blocks.\n"
    "- Maintain a professional business tone.\n"
    "- Ensure the document is fully synthetic and internally consistent.\n"
    "- Length should be approximately 300–500 words.\n"
    "- Do not use placeholder names such as John Doe, ABC Corp, Dummy, Test, or numeric placeholders like 12345.\n"
    "\n"
    "USER INPUT EXAMPLE:\n"
    "- Document Type: HR Personnel Record\n"
    "- Industry: IT Services\n"
    "- Country Format: India\n"
    "- Number of Records: 1\n"
    "\n"
    "INSTRUCTIONS:\n"
    "- Generate the document exactly as specified.\n"
    "- Include all sections in appropriate corporate document style.\n"
    "- Output only the plain-text document with no explanations and no JSON.\n"
    "\n"
    "STRICT PLAIN TEXT RULES:\n"
    "- Do NOT use any Markdown formatting. No **bold**, no *italics*, no headings like ##.\n"
    "- Do NOT output JSON, objects, arrays, or structured formats.\n"
    "- Do NOT use backticks or code fences.\n"
    "- Do NOT include markdown separators like --- or ***.\n"
    "- Do NOT use brackets [], {}, <> unless part of a masked synthetic value.\n"
    "- Use simple text labels for sections (e.g., Employee Information:).\n"
    "- The output must read like a raw text export from internal corporate systems.\n"
    "- If any markdown or code formatting appears, regenerate strictly in plain text.\n"
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
        log_step(logger, "Starting Ollama AI model execution for data generation")
        completed = subprocess.run(
            ["ollama", "run", "tarique_salat/dspm-ai-model:latest", CARD_PROMPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
        )
        raw_output = completed.stdout.strip()
        log_step(logger, "Ollama model execution completed", output_length=len(raw_output))

        cleaned = clean_ollama_output(raw_output)
        log_step(logger, "Cleaned Ollama output", cleaned_length=len(cleaned))

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                log_success(logger, "Parsed JSON data as dictionary", records=1)
                return [data]
            elif isinstance(data, list):
                log_success(logger, "Parsed JSON data as list", records=len(data))
                return data
        except Exception as e:
            log_warning(logger, f"JSON parsing error: {e}", falling_back="entity/value structure")

        # Fallback: wrap cleaned raw text in entity/value structure
        log_step(logger, "Using fallback entity/value structure")
        return [{"entity": "AI_OUTPUT", "value": cleaned}]

    except Exception as e:
        log_error(logger, e, "During Ollama AI model execution")
        return [{"entity": "AI_ERROR", "value": str(e)}]


def process_with_ollama_for_hr_record():
    try:
        log_step(logger, "Starting Ollama AI model execution for HR record generation")
        completed = subprocess.run(
            ["ollama", "run", "tarique_salat/dspm-ai-model:latest", HR_RECORD_PROMPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
        )
        raw_output = completed.stdout.strip()
        log_step(logger, "Ollama model execution for HR completed", output_length=len(raw_output))

        cleaned = clean_ollama_output(raw_output)
        log_step(logger, "Cleaned Ollama HR output", cleaned_length=len(cleaned))

        # HR prompt returns plain text → wrap in a dict for consistency
        return [{"document": cleaned}]
    except Exception as e:
        log_error(logger, e, "During Ollama AI model execution for HR record")
        return [{"document": f"AI_ERROR: {str(e)}"}]


@router.get("/generatedata")
def generate_data(
    filetype: str = Query(..., enum=["json", "pdf", "csv"]),
    # UI sends "PII Data", "Business Document" etc., so no enum here
    datatype: str = Query(...),
    # current_user: dict = Depends(get_current_user)
):
    log_api_request(logger, "GET", "/generatedata", filetype=filetype, datatype=datatype)

    # Normalize datatype from UI
    raw_datatype = datatype
    dt = datatype.strip().lower()

    if dt in ["pii", "pii data", "financial / credit card data"]:
        datatype = "pii"
    elif dt in ["business", "business document", "employee / hr data", "hr", "hr record"]:
        datatype = "business"
    else:
        log_error(logger, ValueError(f"Invalid datatype: {raw_datatype}"), "Datatype validation")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datatype: {raw_datatype}. Supported: PII Data, Business Document.",
        )

    try:
        log_step(logger, "Clearing existing files in SAVE_DIR", save_dir=SAVE_DIR)
        # Clear existing files in SAVE_DIR
        cleared_count = 0
        for f in os.listdir(SAVE_DIR):
            file_path = os.path.join(SAVE_DIR, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
                cleared_count += 1
        if cleared_count > 0:
            log_step(logger, f"Cleared {cleared_count} existing file(s) from SAVE_DIR")

        # Cleanup previous artifacts/data.json if present
        artifact_json_path = os.path.join(ARTIFACTS_DIR, "data.json")
        if os.path.exists(artifact_json_path):
            os.remove(artifact_json_path)
            log_step(logger, "Removed previous artifacts/data.json")

        # ----- INTEGRATE OLLAMA MODEL BASED ON DATATYPE -----
        if datatype == "pii":
            log_step(logger, "Processing PII data with Ollama AI model (credit card / personal info)")
            processed_data = process_with_ollama_for_credit_cards()
        elif datatype == "business":
            log_step(logger, "Processing Business HR record with Ollama AI model")
            processed_data = process_with_ollama_for_hr_record()
        else:
            # This should never hit because of normalization above
            log_error(logger, ValueError(f"Invalid datatype: {datatype}"), "Datatype validation (post-normalization)")
            raise HTTPException(status_code=400, detail="Invalid datatype")

        # Normalize always to list of dicts
        if isinstance(processed_data, dict):
            processed_data = [processed_data]

        log_step(logger, f"Generating {filetype} file", records=len(processed_data), datatype=datatype)
        filename = os.path.join(SAVE_DIR, f"data.{filetype}")
        media_type = "application/octet-stream"

        # ---------- JSON ----------
        if filetype == "json":
            if datatype == "business":
                # For now we don't support JSON for business HR records
                log_error(logger, ValueError("JSON not supported for business datatype"), "Filetype validation")
                raise HTTPException(
                    status_code=400,
                    detail="For business documents, only PDF export is supported currently.",
                )

            log_step(logger, "Writing JSON file (PII)")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            media_type = "application/json"
            log_success(logger, "JSON file generated", filename=filename, records=len(processed_data))

        # ---------- CSV ----------
        elif filetype == "csv":
            if datatype == "business":
                # For now we don't support CSV for business HR records
                log_error(logger, ValueError("CSV not supported for business datatype"), "Filetype validation")
                raise HTTPException(
                    status_code=400,
                    detail="For business documents, only PDF export is supported currently.",
                )

            log_step(logger, "Writing CSV file (PII)")
            fieldnames = [
                "fullName",
                "email",
                "ssnNumber",
                "drivingLicenseNumber",
                "passportNumber",
                "dateOfBirth",
                "address",
            ]
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in processed_data:
                    address = row.get("address", "")
                    if isinstance(address, dict):
                        address = ", ".join(f"{k}: {v}" for k, v in address.items())
                    writer.writerow(
                        {
                            "fullName": row.get("fullName", ""),
                            "email": row.get("email", ""),
                            "ssnNumber": row.get("ssnNumber", ""),
                            "drivingLicenseNumber": row.get("drivingLicenseNumber", ""),
                            "passportNumber": row.get("passportNumber", ""),
                            "dateOfBirth": row.get("dateOfBirth", ""),
                            "address": address,
                        }
                    )
            media_type = "text/csv"
            log_success(logger, "CSV file generated", filename=filename, records=len(processed_data))

        # ---------- PDF ----------
        elif filetype == "pdf":
            log_step(logger, "Generating PDF file")
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", style="B", size=14)

            if datatype == "pii":
                # PII PDF layout (same as your current one)
                pdf.cell(0, 10, txt="Generated Personal Information Test Data", ln=1)
                pdf.ln(3)

                keys = [
                    "fullName",
                    "email",
                    "ssnNumber",
                    "drivingLicenseNumber",
                    "passportNumber",
                    "dateOfBirth",
                    "address",
                ]

                # Dynamically calculate the widest key
                max_key_width = max(pdf.get_string_width(key + ":") for key in keys) + 5

                for idx, entry in enumerate(processed_data, start=1):
                    pdf.set_font("Arial", style="B", size=12)
                    pdf.cell(0, 8, txt=f"Entry {idx}", ln=1)
                    pdf.set_font("Arial", size=11)

                    for key in keys:
                        value = entry.get(key, "")
                        if isinstance(value, dict):
                            value = ", ".join(f"{k}: {v}" for k, v in value.items())

                        # Key column
                        pdf.set_font("Arial", style="B", size=11)
                        pdf.cell(max_key_width, 8, txt=f"{key}:", ln=0)

                        # Value column (wrapped if too long)
                        pdf.set_font("Arial", size=11)
                        pdf.multi_cell(0, 8, txt=str(value))

                    pdf.ln(3)

            elif datatype == "business":
                # Business document: HR record as plain text
                pdf.cell(0, 10, txt="Generated HR Personnel Record (Synthetic)", ln=1)
                pdf.ln(5)
                pdf.set_font("Arial", size=11)

                # We currently expect one HR document, but loop for safety
                for idx, entry in enumerate(processed_data, start=1):
                    if len(processed_data) > 1:
                        pdf.set_font("Arial", style="B", size=12)
                        pdf.cell(0, 8, txt=f"Document {idx}", ln=1)
                        pdf.ln(2)
                        pdf.set_font("Arial", size=11)

                    document_text = entry.get("document", "")
                    pdf.multi_cell(0, 7, txt=document_text)
                    pdf.ln(5)

            pdf.output(filename)
            media_type = "application/pdf"
            log_success(logger, "PDF file generated", filename=filename, records=len(processed_data))

        else:
            log_error(logger, ValueError(f"Invalid file type: {filetype}"), "File type validation")
            raise HTTPException(status_code=400, detail="Invalid file type")

        # Save a JSON copy in artifacts/data.json (for both datatypes)
        log_step(logger, "Saving JSON copy to artifacts/data.json")
        with open(artifact_json_path, "w", encoding="utf-8") as af:
            json.dump(processed_data, af, indent=2, ensure_ascii=False)
        log_success(logger, "JSON copy saved to artifacts", path=artifact_json_path)

        log_api_response(
            logger,
            "GET",
            "/generatedata",
            status_code=200,
            filetype=filetype,
            datatype=datatype,
            filename=os.path.basename(filename),
        )
        return FileResponse(filename, media_type=media_type, filename=os.path.basename(filename))

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During data generation")
        raise HTTPException(status_code=500, detail=f"Failed to generate data: {str(e)}")


@router.post("/uploadtobucket")
def upload_to_bucket(
    current_user: dict = Depends(get_current_user),
):
    log_api_request(logger, "POST", "/uploadtobucket", username=current_user.get("username"))

    try:
        log_step(logger, "Auto-detecting filetype from available files")
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
            log_error(logger, FileNotFoundError("No generated file found"), "File detection")
            raise HTTPException(status_code=404, detail="No generated file found. Please generate the file first.")

        log_success(logger, "File detected", filetype=filetype, filename=filename)

        # Get user id from DB
        log_step(logger, "Fetching user from database", username=current_user.get("username"))
        user = users_collection.find_one({"username": current_user["username"]})
        if not user:
            log_error(logger, ValueError("User not found"), f"User lookup: {current_user.get('username')}")
            raise HTTPException(status_code=404, detail="User not found in DB.")
        user_id = str(user["_id"])
        log_success(logger, "User found", user_id=user_id)

        # AWS credentials from ENV
        log_step(logger, "Retrieving AWS credentials from environment")
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
            log_error(logger, ValueError("AWS credentials not set"), "Environment variable check")
            raise HTTPException(status_code=500, detail="AWS credentials not set in ENV.")
        log_success(logger, "AWS credentials retrieved", region=AWS_REGION)

        log_step(logger, "Creating S3 client")
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )

        # Create bucket name with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        bucket_name = f"neo-bucket-{timestamp}"
        log_step(logger, "Creating S3 bucket", bucket_name=bucket_name, region=AWS_REGION)

        # Create bucket
        try:
            if AWS_REGION == "us-east-1":
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
                )
            log_success(logger, "S3 bucket created", bucket_name=bucket_name)
        except Exception as e:
            log_error(logger, e, f"Failed to create S3 bucket: {bucket_name}")
            raise HTTPException(status_code=500, detail=f"Failed to create bucket: {e}")

        # S3 key: userID/data.filetype
        s3_key = f"{user_id}/data.{filetype}"
        log_step(logger, "Uploading file to S3", bucket=bucket_name, s3_key=s3_key)

        try:
            s3.upload_file(filename, bucket_name, s3_key)
            log_success(logger, "File uploaded to S3", bucket=bucket_name, s3_key=s3_key)
        except Exception as e:
            log_error(logger, e, f"Failed to upload file to S3: {bucket_name}/{s3_key}")
            raise HTTPException(status_code=500, detail=f"Failed to upload to S3: {e}")

        file_url = f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        log_api_response(logger, "POST", "/uploadtobucket", status_code=200, bucket_name=bucket_name)
        return {"msg": "File uploaded successfully", "bucket_name": bucket_name, "file_url": file_url}

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During bucket upload")
        raise HTTPException(status_code=500, detail=f"Failed to upload to bucket: {str(e)}")


# Delete an AWS S3 bucket by name
@router.delete("/deletebucket")
def delete_bucket(bucket_name: str = Query(...), current_user: dict = Depends(get_current_user)):
    log_api_request(
        logger,
        "DELETE",
        "/deletebucket",
        bucket_name=bucket_name,
        username=current_user.get("username"),
    )

    try:
        log_step(logger, "Retrieving AWS credentials from environment")
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
            log_error(logger, ValueError("AWS credentials not set"), "Environment variable check")
            raise HTTPException(status_code=500, detail="AWS credentials not set in ENV.")

        log_step(logger, "Creating S3 client")
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )

        # First, delete all objects in the bucket
        log_step(logger, "Listing objects in bucket before deletion", bucket=bucket_name)
        try:
            # List objects in the bucket
            objects = s3.list_objects_v2(Bucket=bucket_name)
            if "Contents" in objects:
                object_count = len(objects["Contents"])
                log_step(logger, f"Found {object_count} object(s) to delete", bucket=bucket_name)
                for obj in objects["Contents"]:
                    s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
                log_success(logger, f"Deleted {object_count} object(s) from bucket", bucket=bucket_name)
            else:
                log_step(logger, "No objects found in bucket", bucket=bucket_name)

            # Delete the bucket
            log_step(logger, "Deleting S3 bucket", bucket=bucket_name)
            s3.delete_bucket(Bucket=bucket_name)
            log_success(logger, "S3 bucket deleted successfully", bucket=bucket_name)
        except Exception as e:
            log_error(logger, e, f"Failed to delete bucket: {bucket_name}")
            raise HTTPException(status_code=500, detail=f"Failed to delete bucket: {e}")

        log_api_response(logger, "DELETE", "/deletebucket", status_code=200, bucket_name=bucket_name)
        return {"msg": f"Bucket '{bucket_name}' deleted successfully."}

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During bucket deletion")
        raise HTTPException(status_code=500, detail=f"Failed to delete bucket: {str(e)}")
