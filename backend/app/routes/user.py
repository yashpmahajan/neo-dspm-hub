from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.models.user import User
from app.db.mongodb import users_collection
from app.auth.jwt_handler import create_token, decode_token
from app.utils.logger_helper import get_logger, log_api_request, log_api_response, log_error, log_step, log_success, log_warning

logger = get_logger("user")

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/create-user")
def create_user(user: User):
    log_api_request(logger, "POST", "/create-user", username=user.username)
    
    try:
        log_step(logger, "Checking if username already exists", username=user.username)
        if users_collection.find_one({"username": user.username}):
            log_warning(logger, "Username already exists", username=user.username)
            raise HTTPException(status_code=400, detail="Username already exists")
        
        log_step(logger, "Inserting new user into database", username=user.username)
        users_collection.insert_one(user.dict())
        log_success(logger, "User created successfully", username=user.username)
        
        log_api_response(logger, "POST", "/create-user", status_code=200, username=user.username)
        return {"msg": "User created successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, f"During user creation: {user.username}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    log_api_request(logger, "POST", "/login", username=form_data.username)
    
    try:
        log_step(logger, "Looking up user in database", username=form_data.username)
        user = users_collection.find_one({"username": form_data.username})
        
        if not user:
            log_warning(logger, "User not found", username=form_data.username)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        log_step(logger, "Validating password", username=form_data.username)
        if user["password"] != form_data.password:
            log_warning(logger, "Invalid password provided", username=form_data.username)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        log_step(logger, "Creating JWT token", username=form_data.username)
        token = create_token(user["username"], user.get("name", user["username"]))
        log_success(logger, "Login successful", username=form_data.username, user_id=str(user["_id"]))
        
        log_api_response(logger, "POST", "/login", status_code=200, username=form_data.username)
        return {"access_token": token, "userId": str(user["_id"]), "token_type": "bearer"}
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, f"During login: {form_data.username}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        log_step(logger, "Decoding JWT token")
        payload = decode_token(token)
        if not payload:
            log_warning(logger, "Invalid or expired token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        username = payload.get("sub")
        log_step(logger, "Looking up user from token", username=username)
        user = users_collection.find_one({"username": username})
        if not user:
            log_warning(logger, "User not found in database", username=username)
            raise HTTPException(status_code=404, detail="User not found")
        
        log_success(logger, "User authenticated", username=username)
        return user
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, "During user authentication")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.get("/hii")
def say_hii(current_user: dict = Depends(get_current_user)):
    log_api_request(logger, "GET", "/hii", username=current_user.get("username"))
    
    try:
        name = current_user.get('name', current_user['username'])
        log_api_response(logger, "GET", "/hii", status_code=200, username=current_user.get("username"))
        return {"msg": f"Hii {name}"}
    except Exception as e:
        log_error(logger, e, "During /hii endpoint execution")
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")
