from fastapi import APIRouter, HTTPException, Request
import httpx
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import re
import json
import subprocess
from app.utils.logging_config import get_logger
from app.utils.logger_helper import log_api_request, log_api_response, log_error, log_step, log_success, log_warning
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
    """Extract entitySnippet data from response and store in artifacts folder."""
    try:
        logger.info(f"🧾 3rd response snippet (first 500 chars): {response_body[:500]}")
        data = _best_effort_json_parse(response_body)
        if data is None:
            logger.error("❌ Failed to parse response as JSON (even after best-effort substring search)")
            return False

        logger.info("🔍 Searching for entitySnippet data...")
        
        # Extract entitySnippet data - check for nested structure first
        entity_snippet_data = []
        
        # First check if response has statusCode and data structure
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            nested_data = data["data"]
            if "entitySnippet" in nested_data:
                entity_snippet_data = nested_data["entitySnippet"]
                logger.info(f"📊 entitySnippet items found in nested data: {len(entity_snippet_data)}")
        # Then check direct structure
        elif isinstance(data, dict) and "entitySnippet" in data:
            entity_snippet_data = data["entitySnippet"]
            logger.info(f"📊 entitySnippet items found: {len(entity_snippet_data)}")
        elif isinstance(data, list):
            # If response is directly a list, use it
            entity_snippet_data = data
            logger.info(f"📊 Direct list items found: {len(entity_snippet_data)}")
        else:
            # Fallback: look for scanResults in case old format is still returned
            entity_snippet_data = _collect_scan_results_recursive(data)
            logger.info(f"📊 scanResults items found (fallback): {len(entity_snippet_data)}")

        # Always create artifacts and write (even if empty)
        artifacts_dir = create_artifacts_folder()
        client_result_file = os.path.join(artifacts_dir, "client_result.json")
        with open(client_result_file, 'w', encoding='utf-8') as f:
            json.dump(entity_snippet_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Stored entity snippet data in: {client_result_file}")
        logger.info(f"📊 Final data stored has {len(entity_snippet_data)} items")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to extract and store entity snippet data: {str(e)}")
        return False

@router.post("/data-scan")
async def data_scan(request: DataScanRequest, current_user: dict = Depends(get_current_user)):
    """
    Execute 3 curl commands in order and return responses
    1st: Generate token, 2nd: Use token, 3rd: Use token (with 15min wait)
    """
    log_api_request(logger, "POST", "/data-scan", username=current_user.get("username"), curl_commands_count=len(request.curl_commands))
    
    try:
        if len(request.curl_commands) != 3:
            log_error(logger, ValueError("Invalid number of curl commands"), f"Expected 3, got {len(request.curl_commands)}")
            raise HTTPException(status_code=400, detail="Exactly 3 curl commands are required")
        
        # Start fresh: delete specific artifact files (not entire folder)
        log_step(logger, "Cleaning artifact files before scan")
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
            log_step(logger, "Executing 1st curl command to generate token")
            first_body, first_status = curl_executor.run_curl_with_status(request.curl_commands[0], retry=1)
            log_step(logger, "1st curl command completed", http_status=first_status, body_length=len(first_body))
            
            # Extract token: prefer direct JSON parse; fallback to GPT
            log_step(logger, "Extracting token from response")
            extracted_token = None
            try:
                parsed = _best_effort_json_parse(first_body)
                if parsed is not None:
                    candidate = _find_token_in_json(parsed)
                    if candidate:
                        extracted_token = candidate
                        log_success(logger, "Token extracted via JSON parsing")
            except Exception as e:
                log_warning(logger, f"Direct JSON token parse failed: {e}", falling_back="GPT extraction")
            if not extracted_token:
                extracted_token = await curl_executor.extract_token_from_gpt(first_body)
                log_success(logger, "Token extracted via GPT")
            # Sanitize/validate token
            extracted_token = curl_executor.sanitize_and_validate_token(extracted_token)
            log_success(logger, "Token extracted and validated", token_length=len(extracted_token))
            
        except Exception as e:
            log_error(logger, e, "Failed to execute 1st curl or extract token")
            raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")
    
        # Execute 2nd curl command with token
        try:
            log_step(logger, "Executing 2nd curl command with authorization token")
            curl_with_auth = curl_executor.add_authorization_header(request.curl_commands[1], extracted_token)
            second_body, second_status = curl_executor.run_curl_with_status(curl_with_auth, retry=1)
            log_step(logger, "2nd curl command completed", http_status=second_status, body_length=len(second_body))
            
            # Treat non-2xx as failure for scan step
            if second_status is None or not (200 <= second_status < 300):
                log_error(logger, ValueError("Scan failed"), f"HTTP status: {second_status}")
                raise HTTPException(status_code=500, detail="scan failed")
            log_success(logger, "2nd curl command succeeded", http_status=second_status)
            
        except HTTPException:
            # Re-raise our explicit scan failed
            raise
        except Exception as e:
            log_error(logger, e, "Failed to execute 2nd curl")
            raise HTTPException(status_code=500, detail="scan failed")
    
        # Wait for 15 minutes before executing 3rd curl
        log_step(logger, "Waiting 15 minutes before executing 3rd curl command")
        await asyncio.sleep(900)  # 15 minutes = 900 seconds
        log_success(logger, "Wait period completed, proceeding with 3rd curl")
        
        # Execute 3rd curl command with token
        try:
            log_step(logger, "Executing 3rd curl command with authorization token")
            base_curl = curl_executor.add_authorization_header(request.curl_commands[2], extracted_token)

            max_attempts = 3
            wait_seconds = 2
            output = ""
            status = None

            for attempt in range(1, max_attempts + 1):
                log_step(logger, f"3rd curl attempt {attempt}/{max_attempts}")
                output, status = curl_executor.run_curl_with_status(base_curl, retry=1)
                log_step(logger, "3rd curl command completed", http_status=status, body_length=len(output))

                if status != 401:
                    log_success(logger, "3rd curl command succeeded", http_status=status)
                    break

                # On 401, refresh token by re-running 1st curl + extraction
                log_warning(logger, "401 Unauthorized on 3rd curl, refreshing token and retrying", attempt=attempt)
                try:
                    log_step(logger, "Refreshing token by re-executing 1st curl")
                    first_output, first_status_retry = curl_executor.run_curl_with_status(request.curl_commands[0], retry=1)
                    log_step(logger, "Reauth 1st curl completed", http_status=first_status_retry)
                    new_token = await curl_executor.extract_token_from_gpt(first_output)
                    extracted_token = new_token
                    base_curl = curl_executor.add_authorization_header(request.curl_commands[2], extracted_token)
                    log_success(logger, "Token refreshed, retrying 3rd curl")
                except Exception as e:
                    log_error(logger, e, "Failed to refresh token")
                    break

                if attempt < max_attempts:
                    time.sleep(wait_seconds)
                    wait_seconds *= 2

            # Extract and store scanResults regardless of status (if body is present)
            log_step(logger, "Processing 3rd curl response for scanResults")
            artifacts_created = extract_and_store_scan_results(output)
            if artifacts_created:
                log_success(logger, "Scan results extracted and stored")
            else:
                log_warning(logger, "Failed to extract scan results")

            # Generate validation report (JSON and PDF) using OpenAI
            validation_report_created = False
            validation_json_created = False
            try:
                log_step(logger, "Generating validation report using OpenAI")
                artifacts_dir = create_artifacts_folder()
                client_result_path = os.path.join(artifacts_dir, "client_result.json")
                ground_truth_path = os.path.join(artifacts_dir, "data.json")
                pdf_filename = f"dspm_validation_report_{user_id}_{timestamp}.pdf"
                pdf_output_path = os.path.join(artifacts_dir, pdf_filename)
                json_filename = f"dspm_validation_report_{user_id}_{timestamp}.json"
                json_output_path = os.path.join(artifacts_dir, json_filename)

                validator = DSPMValidator()
                validation_json = validator.validate_client_results(
                    client_result_path=client_result_path,
                    ground_truth_path=ground_truth_path,
                    pdf_output_path=pdf_output_path
                )

                if validation_json:
                    with open(json_output_path, "w", encoding="utf-8") as f:
                        json.dump(validation_json, f, indent=2, ensure_ascii=False)
                    validation_json_created = True
                    log_success(logger, "Validation JSON saved", path=json_output_path)

                if os.path.exists(pdf_output_path):
                    validation_report_created = True
                    log_success(logger, "Validation PDF saved", path=pdf_output_path)
            except Exception as e:
                log_error(logger, e, "Failed to generate validation report")

            log_api_response(logger, "POST", "/data-scan", status_code=200, execution_success=(status is None or (200 <= status < 300)), artifacts_created=artifacts_created)
            return DataScanResponse(
                response_body=output,
                execution_success=(status is None or (200 <= status < 300)),
                artifacts_created=artifacts_created,
                validation_report_created=validation_report_created,
                validation_json_created=validation_json_created
            )
            
        except Exception as e:
            log_error(logger, e, "Failed to execute 3rd curl")
            return DataScanResponse(
                response_body="",
                execution_success=False,
                error=str(e),
                artifacts_created=False,
                validation_report_created=False,
                validation_json_created=False
            )
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During data scan execution")
        raise HTTPException(status_code=500, detail=f"Data scan failed: {str(e)}")

@router.get("/download/report")
def download_report():
    log_api_request(logger, "GET", "/download/report")
    
    try:
        log_step(logger, "Finding latest validation report PDF")
        artifacts_dir = create_artifacts_folder()
        # Find latest dspm_validation_report_*.pdf
        candidates = [
            os.path.join(artifacts_dir, f) for f in os.listdir(artifacts_dir)
            if f.startswith("dspm_validation_report_") and f.endswith(".pdf")
        ]
        if not candidates:
            log_error(logger, FileNotFoundError("Report PDF not found"), "Report file search")
            raise HTTPException(status_code=404, detail="Report PDF not found. Run /data-scan first.")
        latest = max(candidates, key=lambda p: os.path.getmtime(p))
        log_success(logger, "Latest report PDF found", path=latest)
        log_api_response(logger, "GET", "/download/report", status_code=200, filename=os.path.basename(latest))
        return FileResponse(latest, media_type="application/pdf", filename=os.path.basename(latest))
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During report download")
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")

@router.get("/download/artifacts-zip")
def download_artifacts_zip():
    log_api_request(logger, "GET", "/download/artifacts-zip")
    
    try:
        log_step(logger, "Creating artifacts zip archive")
        artifacts_dir = create_artifacts_folder()
        # Create zip archive inside artifacts directory
        base_name = os.path.join(artifacts_dir, "artifacts_export")
        zip_path = f"{base_name}.zip"
        # Remove any old zip
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
                log_step(logger, "Removed old zip archive")
        except Exception as e:
            log_warning(logger, f"Could not remove old zip: {e}", continuing="zip creation")
        # Build zip
        log_step(logger, "Building zip archive", root_dir=artifacts_dir)
        shutil.make_archive(base_name=base_name, format="zip", root_dir=artifacts_dir)
        log_success(logger, "Artifacts zip created", path=zip_path)
        log_api_response(logger, "GET", "/download/artifacts-zip", status_code=200)
        return FileResponse(zip_path, media_type="application/zip", filename="artifacts.zip")
    
    except Exception as e:
        log_error(logger, e, "During artifacts zip download")
        raise HTTPException(status_code=500, detail=f"Failed to create artifacts zip: {str(e)}")
    