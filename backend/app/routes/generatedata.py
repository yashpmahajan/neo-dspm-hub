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
    "You are an expert in generating realistic financial information for testing purposes. "
    "Generate 3 realistic credit card entries in JSON format with the following fields: cardHolderName, cardNumber, expirationDate, cvv, cardType, and billingAddress. "
    "Guidelines: The cardHolderName should be a realistic full name. The cardNumber should conform to valid patterns: Visa: starts with 4 and is 16 digits long. MasterCard: starts with 51–55 or 2221–2720 and is 16 digits long. American Express (Amex): starts with 34 or 37 and is 15 digits long. "
    "The expirationDate should be a future date in \"MM/YY\" format, within the next 5 years from current date. "
    "The cvv should: Be 3 digits for Visa and MasterCard. Be 4 digits for Amex. "
    "The billingAddress should be a realistic U.S. address (with street, city, state abbreviation, and ZIP code), and should not contain placeholder or dummy combinations like 1234 or ABCD. "
    "Avoid using dummy values like \"4111 1111 1111 1111\" or \"1234567890123456\". "
    "Everything should appear legitimate and production-like, but not real or tied to real individuals or active financial accounts. "
    "Do not generate any comments."
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
        fieldnames = ["cardHolderName", "cardNumber", "expirationDate", "cvv", "cardType", "billingAddress"]
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in processed_data:
                billing_address = row.get("billingAddress", "")
                if isinstance(billing_address, dict):
                    billing_address = ", ".join(f"{k}: {v}" for k, v in billing_address.items())
                writer.writerow({
                    "cardHolderName": row.get("cardHolderName", ""),
                    "cardNumber": row.get("cardNumber", ""),
                    "expirationDate": row.get("expirationDate", ""),
                    "cvv": row.get("cvv", ""),
                    "cardType": row.get("cardType", ""),
                    "billingAddress": billing_address,
                })
        media_type = "text/csv"

    elif filetype == "pdf":
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(0, 10, txt="Generated Credit Card Test Data", ln=1)
        pdf.ln(3)

        for idx, entry in enumerate(processed_data, start=1):
            pdf.set_font("Arial", style="B", size=12)
            pdf.cell(0, 8, txt=f"Entry {idx}", ln=1)
            pdf.set_font("Arial", size=11)
            for key in ["cardHolderName", "cardNumber", "expirationDate", "cvv", "cardType", "billingAddress"]:
                value = entry.get(key, "")
                if isinstance(value, dict):
                    value = ", ".join(f"{k}: {v}" for k, v in value.items())
                pdf.set_font("Arial", style="B", size=11)
                pdf.cell(40, 8, txt=f"{key}:", ln=0)
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
 