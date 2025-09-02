from fastapi import FastAPI
from app.routes import user, generatedata
from app.core import CORS_ORIGINS
from fastapi.middleware.cors import CORSMiddleware
from app.routes import secretStorage

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://127.0.0.1:8080", 
		"http://localhost:8080",
		"http://192.168.31.236:8080",  # Frontend network IP (old)
		"http://192.168.1.100:8080"  # Frontend current IP
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"]
)

from app.db.mongodb import client, db
import logging

@app.on_event("startup")
def startup_db_check():
	try:
		# Try to list collections to check connection
		db.list_collection_names()
		logging.info("MongoDB connected successfully.")
	except Exception as e:
		logging.error(f"MongoDB connection failed: {e}")
		raise RuntimeError("Failed to connect to MongoDB.")

	# Ensure DB is created by creating a collection if not exists
	if "users" not in db.list_collection_names():
		db.create_collection("users")
		logging.info("'users' collection created.")

app.include_router(user.router)
app.include_router(generatedata.router)
app.include_router(secretStorage.router)