from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(value: str) -> str: return pwd.hash(value)
def verify_password(value: str, hashed: str) -> bool: return pwd.verify(value, hashed)
def create_token(user_id: int, role: str, user_type: str) -> str:
    exp=datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub":str(user_id),"role":role,"type":user_type,"exp":exp}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
def decode_token(token: str) -> dict:
    try: return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc: raise ValueError("Invalid token") from exc

