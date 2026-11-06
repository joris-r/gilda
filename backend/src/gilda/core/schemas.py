from typing import Annotated
from uuid import UUID

import msgspec

from gilda.core.models import Role

NonEmpty = Annotated[str, msgspec.Meta(min_length=1)]
Email = Annotated[str, msgspec.Meta(pattern=r"^[^@\s]+@[^@\s]+$")]
Password = Annotated[str, msgspec.Meta(min_length=8)]
Slug = Annotated[str, msgspec.Meta(pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?\Z", max_length=50)]


class AccountCreate(msgspec.Struct, rename="camel"):
    display_name: NonEmpty
    email: Email
    password: Password


class Credentials(msgspec.Struct):
    email: str
    password: str


class PasswordResetRequest(msgspec.Struct):
    email: Email


class NewPassword(msgspec.Struct):
    password: Password


class AccessLinkRequest(msgspec.Struct):
    email: Email


class UserRead(msgspec.Struct):
    id: UUID
    display_name: str
    email: str


class SessionRead(UserRead):
    superuser: bool


class AssociationCreate(msgspec.Struct):
    name: NonEmpty
    slug: Slug


class AssociationUpdate(msgspec.Struct):
    name: NonEmpty | None = None
    slug: Slug | None = None


class AssociationRead(msgspec.Struct):
    id: UUID
    name: str
    slug: str
    role: Role


class MemberCreate(msgspec.Struct):
    display_name: NonEmpty
    email: Email
    role: Role


class MemberUpdate(msgspec.Struct):
    role: Role


class MemberRead(msgspec.Struct):
    user_id: UUID
    display_name: str
    email: str
    has_account: bool
    email_verified: bool
    access_link: bool
    role: Role


class AssociationDetail(msgspec.Struct):
    id: UUID
    name: str
    slug: str
    timezone: str
    role: Role
    members: list[MemberRead]
