from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    context: str = ""


class SessionCreate(BaseModel):
    title: str = "New writing session"
    client_id: int | None = None


class SessionUpdate(BaseModel):
    title: str | None = None


class GenerateRequest(BaseModel):
    session_id: int
    client_id: int | None = None
    task: str = Field(min_length=5, max_length=10000)


class FeedbackRequest(BaseModel):
    action: str
    rating: int | None = Field(default=None, ge=1, le=5)


class RevisionRequest(BaseModel):
    final_text: str = Field(min_length=1)


class PreferenceUpdate(BaseModel):
    status: str = Field(pattern="^(active|candidate|inactive)$")
