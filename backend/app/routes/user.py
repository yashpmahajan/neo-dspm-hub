from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.models.user import User
from app.db.mongodb import users_collection
from app.auth.jwt_handler import create_token, decode_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/create-user")
def create_user(user: User):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    users_collection.insert_one(user.dict())
    return {"msg": "User created successfully"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"username": form_data.username})
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["username"], user.get("name", user["username"]))
    return {"access_token": token, "userId": str(user["_id"]), "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    username = payload.get("sub")
    user = users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/hii")
def say_hii(current_user: dict = Depends(get_current_user)):
    return {"msg": f"Hii {current_user.get('name', current_user['username'])}"}
