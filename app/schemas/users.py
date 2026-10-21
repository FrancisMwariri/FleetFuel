from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserAdminResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern="^(ORG_ADMIN|FLEET_MANAGER|DRIVER|VIEWER)$")
    reason: str = Field(min_length=5, max_length=500)
