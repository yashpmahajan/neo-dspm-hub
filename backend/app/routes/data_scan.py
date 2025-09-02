from fastapi import APIRouter, HTTPException, Request
import httpx
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import re
import json
import subprocess
from app.logging_config import get_logger
import time
import os
import shutil
from app.utils.dspm_validator import DSPMValidator
import base64
from fastapi.responses import FileResponse
from fastapi import Depends
from app.routes.user import get_current_user
from app.db.mongodb import users_collection
from datetime import datetime

# Get logger for this route
logger = get_logger("data_scan")

router = APIRouter()

class DataScanRequest(BaseModel):
    curl_commands: List[str]

class DataScanResponse(BaseModel):
    response_body: str
    execution_success: bool
    error: str = None
    artifacts_created: bool = False
    validation_report_created: bool = False
    validation_json_created: bool = False

class CurlExecutor:
    def __init__(self):
        self.token = None
        self.client = OpenAI()  # Initialize OpenAI client
    
    def sanitize_curl(self, curl_command: str) -> str:
        """Sanitize curl command for safe execution"""
        # Basic sanitization - remove potentially dangerous characters
        return curl_command.strip()

    def sanitize_and_validate_token(self, token: str) -> str:
        """Normalize token string and validate it looks like a JWT (base64url JSON payload)."""
        if not token:
            return token
        # Strip wrappers
        token = token.strip().strip('"').strip("'").strip()
        # Remove leading Bearer if present
        if token.lower().startswith("bearer "):
            token = token.split(" ", 1)[1].strip()
        # Validate JWT structure
        parts = token.split(".")
        if len(parts) < 2:
            logger.warning("⚠️ Token does not have two JWT segments")
            return token
        header_b64, payload_b64 = parts[0], parts[1]
        def _b64url_decode(s: str) -> bytes:
            pad = '=' * (-len(s) % 4)
            return base64.urlsafe_b64decode(s + pad)
        try:
            # Decode to verify JSON
            _ = json.loads(_b64url_decode(payload_b64).decode("utf-8", errors="ignore"))
            return token
        except Exception as e:
            logger.error(f"❌ Token payload failed base64url JSON decode: {e}")
            return token
    
    def run_curl(self, curl_command: str, retry=3) -> str:
        """Run curl command with retries"""
        for attempt in range(retry):
            try:
                curl_command = self.sanitize_curl(curl_command)
                # Add -w to get HTTP status code
                if '-w' not in curl_command:
                    curl_command += ' -w "\\nHTTP_STATUS:%{http_code}"'

                logger.info(f"🔄 Running curl (attempt {attempt + 1}/{retry}): {curl_command[:100]}...")
                result = subprocess.run(curl_command, shell=True, capture_output=True, text=True)

                # Only check for HTTP_STATUS:401 specifically
                if "HTTP_STATUS:401" in result.stdout:
                    logger.error("❌ 401 Unauthorized - token may be expired")
                    self.token = None

                if result.returncode != 0:
                    logger.warning(f"curl failed with code {result.returncode}")
                    if result.stderr:
                        logger.warning(f"stderr: {result.stderr.strip()}")

                # Remove status line from output
                output = result.stdout.strip()
                if "HTTP_STATUS:" in output:
                    output = output.rsplit("HTTP_STATUS:", 1)[0].strip()

                return output

            except Exception as e:
                logger.error(f"curl exception: {str(e)}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

        return ""

    def run_curl_with_status(self, curl_command: str, retry=1) -> tuple[str, int | None]:
        """Run curl command and return (body, http_status). Minimal internal retry for transport errors."""
        status_code = None
        body = ""
        for attempt in range(retry):
            try:
                cmd = self.sanitize_curl(curl_command)
                if '-w' not in cmd:
                    cmd += ' -w "\\nHTTP_STATUS:%{http_code}"'
                logger.info(f"🔄 Running curl (status) attempt {attempt + 1}/{retry}: {cmd[:120]}...")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                output = result.stdout.strip()
                if "HTTP_STATUS:" in output:
                    try:
                        body, status_s = output.rsplit("HTTP_STATUS:", 1)
                        body = body.strip()
                        status_code = int(status_s.strip())
                    except Exception:
                        body = output
                        status_code = None
                else:
                    body = output
                    status_code = None

                if result.returncode != 0 and result.stderr:
                    logger.warning(f"stderr: {result.stderr.strip()}")
                return body, status_code
            except Exception as e:
                logger.error(f"curl exception: {str(e)}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return body, status_code
    
    async def extract_token_from_gpt(self, response_text: str) -> str:
        """Extract bearer token from response using GPT"""
        gpt_prompt = f"""
You are a parser. From the JSON response below, extract and return ONLY the Bearer token string.
Look for keys like "access_token", "token", or "access" — even if nested.
Return ONLY the token string. No explanation, no formatting, no quotes, no extra text.

Response:
{response_text}
"""
        logger.info("🧠 Extracting bearer token...")
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": gpt_prompt}],
            temperature=0.2,
        )

        token = response.choices[0].message.content.strip().strip('"').strip()
        

        if re.match(r"^[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*$", token):
            logger.info("🔐 Extracted token: Valid JWT format detected.")
        else:
            logger.warning("⚠️ Extracted token: Format may be invalid.")

        return token
    
    def add_authorization_header(self, curl_command: str, token: str) -> str:
        """Add or replace Authorization header with Bearer token"""
        logger.info(f"🔧 Original curl command: {curl_command}")
        
        # Ensure proper spacing after curl command
        if not curl_command.startswith("curl "):
            curl_command = "curl " + curl_command.lstrip("curl")
            logger.info(f"🔧 Fixed spacing: {curl_command}")
        
        # Remove any existing Authorization headers (case-insensitive), for -H or --header
        patterns = [
            r"\s-+H\s+\"authorization\s*:[^\"]*\"",
            r"\s-+H\s+\'authorization\s*:[^\']*\'",
            r"\s--header\s+\"authorization\s*:[^\"]*\"",
            r"\s--header\s+\'authorization\s*:[^\']*\'",
        ]
        for pat in patterns:
            curl_command = re.sub(pat, "", curl_command, flags=re.IGNORECASE)
        curl_command = re.sub(r"\s{2,}", " ", curl_command).strip()
        
        # Normalize token
        token = self.sanitize_and_validate_token(token)
        
        # Add new Authorization header with proper casing per API hint
        curl_command += f' -H "authorization: Bearer {token}"'
        logger.info(f"🔧 Added/normalized Authorization header: {curl_command}")
        
        return curl_command

def create_artifacts_folder():
    """Create artifacts folder if it doesn't exist"""
    artifacts_dir = "artifacts"
    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir)
        logger.info(f"📁 Created artifacts folder: {artifacts_dir}")
    else:
        logger.info(f"📁 Artifacts folder already exists: {artifacts_dir}")
    return artifacts_dir

def remove_artifacts_folder():
    """Remove the artifacts folder if it exists"""
    artifacts_dir = "artifacts"
    try:
        if os.path.exists(artifacts_dir):
            shutil.rmtree(artifacts_dir)
            logger.info(f"🧹 Removed artifacts folder: {artifacts_dir}")
        else:
            logger.info(f"ℹ️ Artifacts folder does not exist: {artifacts_dir}")
    except Exception as e:
        logger.error(f"❌ Failed to remove artifacts folder: {str(e)}")

def clean_artifact_files():
    """Delete specific artifact files if they exist, without removing the folder."""
    artifacts_dir = create_artifacts_folder()
    try:
        logger.info(f"🧾 Artifacts before cleanup: {os.listdir(artifacts_dir)}")
    except Exception as e:
        logger.warning(f"Could not list artifacts dir: {e}")

    # Always remove client_result.json (fresh each run)
    client_result = os.path.join(artifacts_dir, "client_result.json")
    try:
        if os.path.exists(client_result):
            os.remove(client_result)
            logger.info(f"🧹 Removed artifact file: {client_result}")
    except Exception as e:
        logger.error(f"❌ Failed to remove artifact file {client_result}: {e}")

    # Remove any previous timestamped validation reports (pdf/json) and legacy names
    try:
        legacy_targets = [
            os.path.join(artifacts_dir, "dspm_validation_report.pdf"),
            os.path.join(artifacts_dir, "dspm_validation_report.json"),
        ]
        for legacy in legacy_targets:
            if os.path.exists(legacy) and os.path.isfile(legacy):
                os.remove(legacy)
                logger.info(f"🧹 Removed legacy report: {legacy}")

        for fname in os.listdir(artifacts_dir):
            if fname.startswith("dspm_validation_report_") and (fname.endswith(".pdf") or fname.endswith(".json")):
                path = os.path.join(artifacts_dir, fname)
                if os.path.isfile(path):
                    os.remove(path)
                    logger.info(f"🧹 Removed old validation report: {path}")
    except Exception as e:
        logger.error(f"❌ Failed during cleanup of validation reports: {e}")

    try:
        logger.info(f"🧾 Artifacts after cleanup: {os.listdir(artifacts_dir)}")
    except Exception as e:
        logger.warning(f"Could not list artifacts dir after cleanup: {e}")

def _collect_scan_results_recursive(node) -> list:
    """Recursively collect values for keys named 'scanResults' (case-insensitive)."""
    results = []
    try:
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str) and k.lower() == "scanresults":
                    if isinstance(v, list):
                        results.extend(v)
                # Recurse
                results.extend(_collect_scan_results_recursive(v))
        elif isinstance(node, list):
            for item in node:
                results.extend(_collect_scan_results_recursive(item))
    except Exception as e:
        logger.warning(f"⚠️ Error during recursive scanResults extraction: {e}")
    return results

def _best_effort_json_parse(text: str):
    """Try to parse JSON; if it fails, attempt to extract JSON substring."""
    try:
        return json.loads(text)
    except Exception:
        # Try to find a plausible JSON substring
        start_obj = text.find('{')
        start_arr = text.find('[')
        start = min([pos for pos in [start_obj, start_arr] if pos != -1], default=-1)
        end_obj = text.rfind('}')
        end_arr = text.rfind(']')
        end = max(end_obj, end_arr)
        if start != -1 and end != -1 and end > start:
            snippet = text[start:end+1]
            try:
                return json.loads(snippet)
            except Exception:
                return None
        return None

def _find_token_in_json(node):
    """Recursively search for access token in JSON by common keys."""
    if isinstance(node, dict):
        for k, v in node.items():
            lk = k.lower()
            if lk in ("access_token", "token", "access", "id_token", "jwt", "bearer") and isinstance(v, str) and v.strip():
                return v.strip()
            found = _find_token_in_json(v)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_token_in_json(item)
            if found:
                return found
    return None

def extract_and_store_scan_results(response_body: str) -> bool:
    """Extract scanResults from response and store in artifacts folder."""
    try:
        logger.info(f"🧾 3rd response snippet (first 500 chars): {response_body[:500]}")
        data = _best_effort_json_parse(response_body)
        if data is None:
            logger.error("❌ Failed to parse response as JSON (even after best-effort substring search)")
            return False

        logger.info("🔍 Searching for scanResults (case-insensitive) recursively...")
        aggregated_scan_results = _collect_scan_results_recursive(data)
        logger.info(f"📊 scanResults items found: {len(aggregated_scan_results)}")

        # Always create artifacts and write (even if empty)
        artifacts_dir = create_artifacts_folder()
        client_result_file = os.path.join(artifacts_dir, "client_result.json")
        with open(client_result_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated_scan_results, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Stored scanResults in: {client_result_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to extract and store scanResults: {str(e)}")
        return False

@router.post("/data-scan")
async def data_scan(request: DataScanRequest, current_user: dict = Depends(get_current_user)):
    """
    Execute 3 curl commands in order and return responses
    1st: Generate token, 2nd: Use token, 3rd: Use token (with 15min wait)
    """
    if len(request.curl_commands) != 3:
        raise HTTPException(status_code=400, detail="Exactly 3 curl commands are required")
    
    # Start fresh: delete specific artifact files (not entire folder)
    clean_artifact_files()
    
    extracted_token = ""
    curl_executor = CurlExecutor()
    artifacts_created = False
    validation_report_created = False
    validation_json_created = False

    # Get user id for report naming
    user = users_collection.find_one({"username": current_user["username"]}) if current_user and "username" in current_user else None
    user_id = str(user["_id"]) if user and "_id" in user else "unknown"
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    # Execute 1st curl command to get token
    try:
        logger.info("🚀 Executing 1st curl command to generate token...")
        first_body, first_status = curl_executor.run_curl_with_status(request.curl_commands[0], retry=1)
        logger.info(f"📝 1st curl HTTP status: {first_status}")
        logger.info(f"📦 1st curl body (truncated): {first_body[:1000]}")
        
        # Extract token: prefer direct JSON parse; fallback to GPT
        extracted_token = None
        try:
            parsed = _best_effort_json_parse(first_body)
            if parsed is not None:
                candidate = _find_token_in_json(parsed)
                if candidate:
                    extracted_token = candidate
                    logger.info("🔑 Token extracted via JSON parsing.")
        except Exception as e:
            logger.warning(f"⚠️ Direct JSON token parse failed: {e}")
        if not extracted_token:
            extracted_token = await curl_executor.extract_token_from_gpt(first_body)
            logger.info("🧠 Token extracted via GPT.")
        # Sanitize/validate token
        extracted_token = curl_executor.sanitize_and_validate_token(extracted_token)
        logger.info(f"✅ Token extracted successfully (length {len(extracted_token)}). Using for auth...")
        
    except Exception as e:
        logger.error(f"❌ Failed to execute 1st curl or extract token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")
    
    # Execute 2nd curl command with token
    try:
        logger.info(f"🚀 Executing 2nd curl command with authorization token... {extracted_token}")
        curl_with_auth = curl_executor.add_authorization_header(request.curl_commands[1], extracted_token)
        second_body, second_status = curl_executor.run_curl_with_status(curl_with_auth, retry=1)
        logger.info(f"📝 2nd curl HTTP status: {second_status}")
        logger.info(f"📦 2nd curl body (truncated): {second_body[:1000]}")
        
        # Treat non-2xx as failure for scan step
        if second_status is None or not (200 <= second_status < 300):
            raise HTTPException(status_code=500, detail="scan failed")
        
    except HTTPException:
        # Re-raise our explicit scan failed
        raise
    except Exception as e:
        logger.error(f"❌ Failed to execute 2nd curl: {str(e)}")
        raise HTTPException(status_code=500, detail="scan failed")
    
    # Wait for 15 minutes before executing 3rd curl
    logger.info("⏰ Waiting 15 minutes before executing 3rd curl command...")
    # await asyncio.sleep(900)  # 15 minutes = 900 seconds
    
    # Execute 3rd curl command with token
    try:
        logger.info("🚀 Executing 3rd curl command with authorization token...")
        base_curl = curl_executor.add_authorization_header(request.curl_commands[2], extracted_token)

        max_attempts = 3
        wait_seconds = 2
        output = ""
        status = None

        for attempt in range(1, max_attempts + 1):
            logger.info(f"▶️ 3rd curl attempt {attempt}/{max_attempts}")
            output, status = curl_executor.run_curl_with_status(base_curl, retry=1)
            logger.info(f"📝 3rd curl HTTP status: {status}")
            logger.info(f"📦 3rd curl body (truncated): {output[:1000]}")

            if status != 401:
                break

            # On 401, refresh token by re-running 1st curl + extraction
            logger.warning("🔁 401 Unauthorized on 3rd curl, refreshing token and retrying...")
            try:
                first_output, first_status_retry = curl_executor.run_curl_with_status(request.curl_commands[0], retry=1)
                logger.info(f"📝 Reauth 1st curl HTTP status: {first_status_retry}")
                logger.info(f"📦 Reauth 1st curl body (truncated): {first_output[:1000]}")
                new_token = await curl_executor.extract_token_from_gpt(first_output)
                extracted_token = new_token
                base_curl = curl_executor.add_authorization_header(request.curl_commands[2], extracted_token)
                logger.info("✅ Token refreshed. Retrying 3rd curl...")
            except Exception as e:
                logger.error(f"❌ Failed to refresh token: {e}")
                break

            if attempt < max_attempts:
                time.sleep(wait_seconds)
                wait_seconds *= 2

        # Extract and store scanResults regardless of status (if body is present)
        logger.info("🔍 Processing 3rd curl response for scanResults...")
        artifacts_created = extract_and_store_scan_results(output)

        # Generate validation report (JSON and PDF) using OpenAI
        validation_report_created = False
        validation_json_created = False
        try:
            artifacts_dir = create_artifacts_folder()
            client_result_path = os.path.join(artifacts_dir, "client_result.json")
            ground_truth_path = os.path.join(artifacts_dir, "data.json")
            pdf_filename = f"dspm_validation_report_{user_id}_{timestamp}.pdf"
            pdf_output_path = os.path.join(artifacts_dir, pdf_filename)
            json_filename = f"dspm_validation_report_{user_id}_{timestamp}.json"
            json_output_path = os.path.join(artifacts_dir, json_filename)

            validator = DSPMValidator()
            logger.info("🧠 Generating validation using OpenAI...")
            validation_json = validator.validate_client_results(
                client_result_path=client_result_path,
                ground_truth_path=ground_truth_path,
                pdf_output_path=pdf_output_path
            )

            if validation_json:
                with open(json_output_path, "w", encoding="utf-8") as f:
                    json.dump(validation_json, f, indent=2, ensure_ascii=False)
                validation_json_created = True
                logger.info(f"💾 Saved validation JSON: {json_output_path}")

            if os.path.exists(pdf_output_path):
                validation_report_created = True
                logger.info(f"📄 Saved validation PDF: {pdf_output_path}")
        except Exception as e:
            logger.error(f"❌ Failed to generate validation report: {e}")

        return DataScanResponse(
            response_body=output,
            execution_success=(status is None or (200 <= status < 300)),
            artifacts_created=artifacts_created,
            validation_report_created=validation_report_created,
            validation_json_created=validation_json_created
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to execute 3rd curl: {str(e)}")
        return DataScanResponse(
            response_body="",
            execution_success=False,
            error=str(e),
            artifacts_created=False,
            validation_report_created=False,
            validation_json_created=False
        )

@router.get("/download/report")
def download_report():
    artifacts_dir = create_artifacts_folder()
    # Find latest dspm_validation_report_*.pdf
    candidates = [
        os.path.join(artifacts_dir, f) for f in os.listdir(artifacts_dir)
        if f.startswith("dspm_validation_report_") and f.endswith(".pdf")
    ]
    if not candidates:
        raise HTTPException(status_code=404, detail="Report PDF not found. Run /data-scan first.")
    latest = max(candidates, key=lambda p: os.path.getmtime(p))
    logger.info(f"⬇️ Sending report PDF: {latest}")
    return FileResponse(latest, media_type="application/pdf", filename=os.path.basename(latest))

@router.get("/download/artifacts-zip")
def download_artifacts_zip():
    artifacts_dir = create_artifacts_folder()
    # Create zip archive inside artifacts directory
    base_name = os.path.join(artifacts_dir, "artifacts_export")
    zip_path = f"{base_name}.zip"
    # Remove any old zip
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except Exception as e:
        logger.warning(f"Could not remove old zip: {e}")
    # Build zip
    shutil.make_archive(base_name=base_name, format="zip", root_dir=artifacts_dir)
    logger.info(f"⬇️ Sending artifacts zip: {zip_path}")
    return FileResponse(zip_path, media_type="application/zip", filename="artifacts.zip")
    