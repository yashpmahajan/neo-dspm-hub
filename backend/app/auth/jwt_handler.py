import jwt
import datetime


from app.core import JWT_SECRET
ALGORITHM = "HS256"


def create_token(username: str, name: str):
    token_data = {
        "sub": username,
        "name": name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(token_data, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None
