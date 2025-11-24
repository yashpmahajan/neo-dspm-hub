
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.mongodb import db
from cryptography.fernet import Fernet
import os
from app.utils.logger_helper import get_logger, log_api_request, log_api_response, log_error, log_step, log_success, log_warning

logger = get_logger("secretStorage")

router = APIRouter()

# Generate or load encryption key (in production, store securely)
FERNET_KEY = os.environ.get("FERNET_KEY") or Fernet.generate_key()
fernet = Fernet(FERNET_KEY)

class AwsCredsRequest(BaseModel):
	access_key_id: str
	secret_access_key: str
	region: str
	bucket_name: str

class ApiKeyRequest(BaseModel):
	username: str
	apikey: str

class BlobCredsRequest(BaseModel):
	account_name: str
	account_key: str
	container_name: str

class RdsCredsRequest(BaseModel):
	host: str
	port: int
	username: str
	password: str
	database: str
	engine: str

@router.post("/store-aws-creds")
def store_aws_creds(data: AwsCredsRequest):
	log_api_request(logger, "POST", "/store-aws-creds", region=data.region, bucket_name=data.bucket_name)
	
	try:
		log_step(logger, "Determining .env file path")
		# Update .env in NEO-DSPM-HUB root directory
		env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
		log_step(logger, "Reading existing .env file", env_path=env_path)
		
		env_lines = []
		if os.path.exists(env_path):
			with open(env_path, 'r') as f:
				env_lines = f.readlines()
			log_step(logger, "Read existing .env file", lines=len(env_lines))
		else:
			log_step(logger, ".env file does not exist, will create new one", env_path=env_path)
		
		env_dict = {}
		for line in env_lines:
			if '=' in line:
				k, v = line.strip().split('=', 1)
				env_dict[k] = v
		
		log_step(logger, "Updating AWS credentials in .env", region=data.region)
		env_dict['AWS_ACCESS_KEY_ID'] = data.access_key_id
		env_dict['AWS_SECRET_ACCESS_KEY'] = data.secret_access_key
		env_dict['AWS_REGION'] = data.region
		env_dict['AWS_BUCKET_NAME'] = data.bucket_name
		
		log_step(logger, "Writing updated .env file", env_path=env_path)
		with open(env_path, 'w') as f:
			for k, v in env_dict.items():
				f.write(f'{k}={v}\n')
		
		log_success(logger, "AWS credentials stored in .env", region=data.region, bucket_name=data.bucket_name)
		log_api_response(logger, "POST", "/store-aws-creds", status_code=200)
		return {"message": ".env file in NEO-DSPM-HUB updated with AWS credentials successfully"}
	
	except Exception as e:
		log_error(logger, e, "During AWS credentials storage")
		raise HTTPException(status_code=500, detail=f"Failed to store AWS credentials: {str(e)}")

@router.post("/store-apikey")
def store_apikey(data: ApiKeyRequest):
	log_api_request(logger, "POST", "/store-apikey", username=data.username)
	
	try:
		log_step(logger, "Encrypting API key", username=data.username)
		encrypted_apikey = fernet.encrypt(data.apikey.encode()).decode()
		log_success(logger, "API key encrypted successfully")
		
		log_step(logger, "Updating user record with encrypted API key", username=data.username)
		result = db["users"].update_one(
			{"username": data.username},
			{"$set": {"apikey": encrypted_apikey}}
		)
		
		if result.matched_count == 0:
			log_warning(logger, "User not found in database", username=data.username)
			raise HTTPException(status_code=404, detail="User not found")
		
		log_success(logger, "API key stored successfully", username=data.username, matched_count=result.matched_count)
		log_api_response(logger, "POST", "/store-apikey", status_code=200, username=data.username)
		return {"message": "API key stored successfully"}
	
	except HTTPException:
		raise
	except Exception as e:
		log_error(logger, e, f"During API key storage: {data.username}")
		raise HTTPException(status_code=500, detail=f"Failed to store API key: {str(e)}")


	
@router.post("/store-blob-creds")
def store_blob_creds(data: BlobCredsRequest):
	log_api_request(logger, "POST", "/store-blob-creds", account_name=data.account_name, container_name=data.container_name)
	
	try:
		log_step(logger, "Determining .env file path")
		# Update .env in NEO-DSPM-HUB root directory
		env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
		log_step(logger, "Reading existing .env file", env_path=env_path)
		
		env_lines = []
		if os.path.exists(env_path):
			with open(env_path, 'r') as f:
				env_lines = f.readlines()
			log_step(logger, "Read existing .env file", lines=len(env_lines))
		else:
			log_step(logger, ".env file does not exist, will create new one", env_path=env_path)
		
		env_dict = {}
		for line in env_lines:
			if '=' in line:
				k, v = line.strip().split('=', 1)
				env_dict[k] = v
		
		log_step(logger, "Updating Azure Blob credentials in .env", account_name=data.account_name, container_name=data.container_name)
		env_dict['AZURE_STORAGE_ACCOUNT_NAME'] = data.account_name
		env_dict['AZURE_STORAGE_ACCOUNT_KEY'] = data.account_key
		env_dict['AZURE_BLOB_CONTAINER'] = data.container_name
		
		log_step(logger, "Writing updated .env file", env_path=env_path)
		with open(env_path, 'w') as f:
			for k, v in env_dict.items():
				f.write(f'{k}={v}\n')
		
		log_success(logger, "Azure Blob credentials stored in .env", account_name=data.account_name, container_name=data.container_name)
		log_api_response(logger, "POST", "/store-blob-creds", status_code=200)
		return {"message": ".env file in NEO-DSPM-HUB updated with Azure Blob credentials successfully"}
	
	except Exception as e:
		log_error(logger, e, "During Azure Blob credentials storage")
		raise HTTPException(status_code=500, detail=f"Failed to store Azure Blob credentials: {str(e)}")
 
 
@router.post("/store-rds-creds")
def store_rds_creds(data: RdsCredsRequest):
	log_api_request(logger, "POST", "/store-rds-creds", host=data.host, port=data.port, database=data.database, engine=data.engine)
	
	try:
		log_step(logger, "Determining .env file path")
		# Update .env in NEO-DSPM-HUB root directory
		env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
		log_step(logger, "Reading existing .env file", env_path=env_path)
		
		env_lines = []
		if os.path.exists(env_path):
			with open(env_path, 'r') as f:
				env_lines = f.readlines()
			log_step(logger, "Read existing .env file", lines=len(env_lines))
		else:
			log_step(logger, ".env file does not exist, will create new one", env_path=env_path)
		
		env_dict = {}
		for line in env_lines:
			if '=' in line:
				k, v = line.strip().split('=', 1)
				env_dict[k] = v
		
		log_step(logger, "Updating RDS credentials in .env", host=data.host, port=data.port, database=data.database, engine=data.engine)
		env_dict['RDS_HOST'] = data.host
		env_dict['RDS_PORT'] = str(data.port)
		env_dict['RDS_USERNAME'] = data.username
		env_dict['RDS_PASSWORD'] = data.password
		env_dict['RDS_DB_NAME'] = data.database
		env_dict['RDS_ENGINE'] = data.engine
		
		log_step(logger, "Writing updated .env file", env_path=env_path)
		with open(env_path, 'w') as f:
			for k, v in env_dict.items():
				f.write(f'{k}={v}\n')
		
		log_success(logger, "RDS credentials stored in .env", host=data.host, port=data.port, database=data.database, engine=data.engine)
		log_api_response(logger, "POST", "/store-rds-creds", status_code=200)
		return {"message": ".env file in NEO-DSPM-HUB updated with RDS credentials successfully"}
	
	except Exception as e:
		log_error(logger, e, "During RDS credentials storage")
		raise HTTPException(status_code=500, detail=f"Failed to store RDS credentials: {str(e)}")