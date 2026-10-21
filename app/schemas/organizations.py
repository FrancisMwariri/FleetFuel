from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=80, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    default_currency: str = Field(min_length=3, max_length=3, pattern="^[A-Z]{3}$")

    @field_validator("default_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    default_currency: str


class OrganizationUpdate(BaseModel):
    status: str = Field(pattern="^(ACTIVE|SUSPENDED)$")
    reason: str = Field(min_length=5, max_length=500)


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(ORG_ADMIN|FLEET_MANAGER|DRIVER|VIEWER)$")


class InvitationResponse(BaseModel):
    invitation_token: str
    expires_at: str


class RegistrationRequest(BaseModel):
    invitation_token: str = Field(min_length=40, max_length=200)
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=256)
