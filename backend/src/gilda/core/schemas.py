from typing import Annotated
from uuid import UUID

import msgspec

from gilda.core.models import Role

NonEmpty = Annotated[str, msgspec.Meta(min_length=1)]
Email = Annotated[str, msgspec.Meta(pattern=r"^[^@\s]+@[^@\s]+$")]
Password = Annotated[str, msgspec.Meta(min_length=8)]


class AccountCreate(msgspec.Struct):
    display_name: NonEmpty
    email: Email
    password: Password


class Credentials(msgspec.Struct):
    email: str
    password: str


class VerifyRequest(msgspec.Struct):
    token: str


class ResendRequest(msgspec.Struct):
    email: Email


class UserRead(msgspec.Struct):
    id: UUID
    display_name: str
    email: str


class AssociationCreate(msgspec.Struct):
    name: NonEmpty


class AssociationRead(msgspec.Struct):
    id: UUID
    name: str
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
    role: Role


class AssociationDetail(msgspec.Struct):
    id: UUID
    name: str
    timezone: str
    role: Role
    members: list[MemberRead]
