from fastapi import Depends, Header, HTTPException
from jose import jwt, JWTError
from amna_rag.config import settings

class CurrentUser:
    def __init__(self, user_id: str, role: str):
        self.id = user_id
        self.role = role.lower()

def get_current_user(authorization: str | None = Header(default=None), x_user_id: str | None = Header(default=None), x_user_role: str | None = Header(default=None)) -> CurrentUser:
    """Verify Huda's JWT. Dev headers are available only when ALLOW_DEV_AUTH=true."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            user_id = str(payload.get("sub") or payload.get("user_id") or "")
            role = str(payload.get("role") or "employee").lower().replace(" ", "_")
            if role == "agent": role = "support_agent"
            if not user_id:
                raise HTTPException(status_code=401, detail="JWT is missing user identity")
            return CurrentUser(user_id, role)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
    if settings.allow_dev_auth and x_user_id:
        role = (x_user_role or "employee").lower().replace(" ", "_")
        if role == "agent": role = "support_agent"
        return CurrentUser(x_user_id, role)
    raise HTTPException(status_code=401, detail="Provide Huda's Bearer JWT token")

def require_roles(*roles):
    def check(user: CurrentUser = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user
    return check
