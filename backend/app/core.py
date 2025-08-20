import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
