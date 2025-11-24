from fastapi import FastAPI
from app.routes import user, generatedata, secretStorage, data_scan
from app.core import CORS_ORIGINS
from fastapi.middleware.cors import CORSMiddleware
from app.routes import secretStorage
from app.utils.logging_config import setup_route_logging
import logging
from app.utils.logging_config import get_logger
from app.routes import upload_to_env_bucket

# Setup logging for all routes
setup_route_logging()

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

@app.on_event("startup")
def startup_db_check():
	try:
		# Try to list collections to check connection
		db.list_collection_names()
		logger = get_logger("main")
		logger.info("MongoDB connected successfully.")
	except Exception as e:
		logger = get_logger("main")
		logger.error(f"MongoDB connection failed: {e}")
		raise RuntimeError("Failed to connect to MongoDB.")

	# Ensure DB is created by creating a collection if not exists
	if "users" not in db.list_collection_names():
		db.create_collection("users")
		logger = get_logger("main")
		logger.info("'users' collection created.")

app.include_router(user.router)
app.include_router(generatedata.router)
app.include_router(secretStorage.router)
app.include_router(data_scan.router)
app.include_router(upload_to_env_bucket.router)



# Log all registered routes
@app.on_event("startup")
def log_routes():
    logger = get_logger("main")
    logger.info("📋 Registered routes:")
    for route in app.routes:
        if hasattr(route, 'path'):
            logger.info(f"  {route.methods} {route.path}")
    logger.info("✅ All routes registered successfully")