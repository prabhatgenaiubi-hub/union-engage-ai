from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.models import User
bearer=HTTPBearer(auto_error=False)
def current_user(credentials: HTTPAuthorizationCredentials|None=Depends(bearer), db: Session=Depends(get_db)) -> User:
    if not credentials: raise HTTPException(401,"Authentication required")
    try: payload=decode_token(credentials.credentials)
    except ValueError: raise HTTPException(401,"Invalid or expired token")
    user=db.get(User,int(payload["sub"]))
    if not user: raise HTTPException(401,"User not found")
    return user
def bank_user(user: User=Depends(current_user)) -> User:
    if user.user_type!="employee": raise HTTPException(403,"Bank access required")
    return user
def admin_user(user: User=Depends(bank_user)) -> User:
    if user.role!="admin": raise HTTPException(403,"Admin access required")
    return user

