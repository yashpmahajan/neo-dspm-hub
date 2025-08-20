from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from app.db.mongodb import db
from cryptography.fernet import Fernet
import os

# Generate or load encryption key (in production, store securely)
FERNET_KEY = os.environ.get("FERNET_KEY") or Fernet.generate_key()
fernet = Fernet(FERNET_KEY)

router = APIRouter()

class ApiKeyRequest(BaseModel):
	username: str
	apikey: str

@router.post("/store-apikey")
def store_apikey(data: ApiKeyRequest):
	# Encrypt the API key
	encrypted_apikey = fernet.encrypt(data.apikey.encode()).decode()
	# Update user document in MongoDB
	result = db["users"].update_one(
		{"username": data.username},
		{"$set": {"apikey": encrypted_apikey}}
	)
	if result.matched_count == 0:
		raise HTTPException(status_code=404, detail="User not found")
	return {"message": "API key stored successfully"}
