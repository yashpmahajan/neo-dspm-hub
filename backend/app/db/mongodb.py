from pymongo import MongoClient
from app.core import MONGODB_URL

client = MongoClient(MONGODB_URL)
# Use the database name you want to use (e.g., 'neo_dspm')
db = client["DSPM"]
# Use the collection name you want to use (e.g., 'users')
users_collection = db["DSPM"]
