from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from bson.objectid import ObjectId
import jwt
import datetime

app = FastAPI()

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["neo_dspm"]
users_collection = db["users"]

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

class User(BaseModel):
    username: str
    password: str
    name: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@app.post("/create-user")
def create_user(user: User):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    user_dict = user.dict()
    users_collection.insert_one(user_dict)
    return {"msg": "User created successfully"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"username": form_data.username})
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token_data = {
        "sub": user["username"],
        "name": user.get("name", user["username"]),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = users_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/hii")
def say_hii(current_user: dict = Depends(get_current_user)):
    return {"msg": f"Hii {current_user.get('name', current_user['username'])}"}
