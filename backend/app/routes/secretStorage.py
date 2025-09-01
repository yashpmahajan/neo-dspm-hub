
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.mongodb import db
from cryptography.fernet import Fernet
import os

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

@router.post("/store-aws-creds")
def store_aws_creds(data: AwsCredsRequest):
	# Update .env in NEO-DSPM-HUB root directory
	env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
	env_lines = []
	if os.path.exists(env_path):
		with open(env_path, 'r') as f:
			env_lines = f.readlines()
	env_dict = {}
	for line in env_lines:
		if '=' in line:
			k, v = line.strip().split('=', 1)
			env_dict[k] = v
	env_dict['AWS_ACCESS_KEY_ID'] = data.access_key_id
	env_dict['AWS_SECRET_ACCESS_KEY'] = data.secret_access_key
	env_dict['AWS_REGION'] = data.region
	env_dict['AWS_BUCKET_NAME'] = data.bucket_name
	with open(env_path, 'w') as f:
		for k, v in env_dict.items():
			f.write(f'{k}={v}\n')
	return {"message": ".env file in NEO-DSPM-HUB updated with AWS credentials successfully"}

@router.post("/store-apikey")
def store_apikey(data: ApiKeyRequest):
	encrypted_apikey = fernet.encrypt(data.apikey.encode()).decode()
	result = db["users"].update_one(
		{"username": data.username},
		{"$set": {"apikey": encrypted_apikey}}
	)
	if result.matched_count == 0:
		raise HTTPException(status_code=404, detail="User not found")
	return {"message": "API key stored successfully"}
