from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: str
    password: str
    name: Optional[str] = None
    permission: str = "user"
