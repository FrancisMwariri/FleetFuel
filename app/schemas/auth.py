from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=40, max_length=200)
    new_password: str = Field(min_length=12, max_length=256)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1200


class UserResponse(BaseModel):
    id: str
    organization_id: str | None
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
