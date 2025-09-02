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

class CurlExecutor:
    def __init__(self):
        self.token = None
        self.client = OpenAI()  # Initialize OpenAI client
    
    def sanitize_curl(self, curl_command: str) -> str:
        """Sanitize curl command for safe execution"""
        # Basic sanitization - remove potentially dangerous characters
        return curl_command.strip()
    
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
        
        # Check if Authorization header already exists
        if '-H "Authorization:' in curl_command or "-H 'Authorization:" in curl_command:
            # Replace existing Authorization header
            curl_command = re.sub(r'-H ["\']Authorization:[^"\']*["\']', f'-H "Authorization: Bearer {token}"', curl_command)
            logger.info(f"🔧 Replaced existing Authorization header: {curl_command}")
        else:
            # Add new Authorization header with proper spacing
            curl_command += f' -H "Authorization: Bearer {token}"'
            logger.info(f"🔧 Added new Authorization header: {curl_command}")
        
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
async def data_scan(request: DataScanRequest):
    """
    Execute 3 curl commands in order and return responses
    1st: Generate token, 2nd: Use token, 3rd: Use token (with 15min wait)
    """
    if len(request.curl_commands) != 3:
        raise HTTPException(status_code=400, detail="Exactly 3 curl commands are required")
    
    # Always start fresh: remove artifacts folder at the beginning
    remove_artifacts_folder()
    
    extracted_token = ""
    curl_executor = CurlExecutor()
    artifacts_created = False
    
    # Execute 1st curl command to get token
    try:
        logger.info("🚀 Executing 1st curl command to generate token...")
        output = curl_executor.run_curl(request.curl_commands[0])
        logger.info(f"🔍 1st curl response: {output}")
        # Extract token using OpenAI
        extracted_token = await curl_executor.extract_token_from_gpt(output)
        logger.info(f"✅ Token extracted successfully: {extracted_token}...")
        
    except Exception as e:
        logger.error(f"❌ Failed to execute 1st curl or extract token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")
    
    # Execute 2nd curl command with token
    try:
        logger.info(f"🚀 Executing 2nd curl command with authorization token... {extracted_token}")
        curl_with_auth = curl_executor.add_authorization_header(request.curl_commands[1], extracted_token)
        curl_executor.run_curl(curl_with_auth)
        
    except Exception as e:
        logger.error(f"❌ Failed to execute 2nd curl: {str(e)}")
        raise HTTPException(status_code=500, detail="scan failed")
    
    # Wait for 15 minutes before executing 3rd curl
    logger.info("⏰ Waiting 15 minutes before executing 3rd curl command...")
    # await asyncio.sleep(900)  # 15 minutes = 900 seconds
    
    # Execute 3rd curl command with token
    try:
        logger.info("🚀 Executing 3rd curl command with authorization token...")
        curl_with_auth = curl_executor.add_authorization_header(request.curl_commands[2], extracted_token)
        output = curl_executor.run_curl(curl_with_auth)
        
        # Extract and store scanResults
        logger.info("🔍 Processing 3rd curl response for scanResults...")
        artifacts_created = extract_and_store_scan_results(output)
        
        return DataScanResponse(
            response_body=output,
            execution_success=True,
            artifacts_created=artifacts_created
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to execute 3rd curl: {str(e)}")
        return DataScanResponse(
            response_body="",
            execution_success=False,
            error=str(e),
            artifacts_created=False
        )
    