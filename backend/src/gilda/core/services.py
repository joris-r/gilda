import secrets
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from litestar.exceptions import (
    ClientException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.status_codes import HTTP_409_CONFLICT
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import Association, EmailVerificationToken, Membership, Role, User
from gilda.core.repositories import (
    AssociationRepository,
    EmailVerificationTokenRepository,
    MembershipRepository,
    UserRepository,
)
from gilda.core.schemas import AssociationDetail, AssociationRead, MemberRead
from gilda.mailer import send_verification_email

_hasher = PasswordHasher()
TOKEN_LIFETIME = timedelta(hours=24)


class ConflictException(ClientException):
    status_code = HTTP_409_CONFLICT


def member_read(membership: Membership) -> MemberRead:
    user = membership.user
    return MemberRead(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        has_account=user.has_account,
        email_verified=user.email_verified,
        role=cast(Role, membership.role),
    )


class AccountService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.users = UserRepository(session=db_session)
        self.tokens = EmailVerificationTokenRepository(session=db_session)

    async def find_by_email(self, email: str) -> User | None:
        return await self.users.get_one_or_none(email=email.lower())

    async def create_account(self, display_name: str, email: str, password: str) -> User:
        password_hash = _hasher.hash(password)
        user = await self.find_by_email(email)
        if user is None:
            user = await self.users.add(
                User(display_name=display_name, email=email.lower(), password_hash=password_hash)
            )
        elif user.has_account:
            raise ConflictException("An account already exists for this email.")
        else:
            # R2: the account takes over the user a manager added.
            user.display_name = display_name
            user.password_hash = password_hash
            user = await self.users.update(user)
        await self._issue_token(user)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.find_by_email(email)
        if user is None or user.password_hash is None:
            raise NotAuthorizedException("Wrong email or password.")
        try:
            _hasher.verify(user.password_hash, password)
        except VerificationError as error:
            raise NotAuthorizedException("Wrong email or password.") from error
        if not user.email_verified:
            raise NotAuthorizedException("Wrong email or password.")
        return user

    async def get(self, user_id: UUID) -> User | None:
        return await self.users.get_one_or_none(id=user_id)

    async def confirm(self, token: str) -> User:
        record = await self.tokens.get_one_or_none(token=token)
        if record is None or record.expires_at < datetime.now(UTC):
            raise NotFoundException("This confirmation link is unknown or expired.")
        user = await self.get(record.user_id)
        assert user is not None  # the foreign key guarantees it
        user.email_verified_at = datetime.now(UTC)
        await self.users.update(user)
        await self.tokens.delete(record.id)
        return user

    async def resend_confirmation(self, email: str) -> None:
        user = await self.find_by_email(email)
        if user is not None and not user.email_verified:
            await self._issue_token(user)

    async def _issue_token(self, user: User) -> None:
        # R8: a new token replaces any pending one.
        existing = await self.tokens.get_one_or_none(user_id=user.id)
        if existing is not None:
            await self.tokens.delete(existing.id)
        token = await self.tokens.add(
            EmailVerificationToken(
                user_id=user.id,
                token=secrets.token_urlsafe(32),
                expires_at=datetime.now(UTC) + TOKEN_LIFETIME,
            )
        )
        send_verification_email(user.email, token.token)


class AssociationService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.users = UserRepository(session=db_session)
        self.associations = AssociationRepository(session=db_session)
        self.memberships = MembershipRepository(session=db_session)

    async def list_for(self, user: User) -> list[AssociationRead]:
        memberships = await self.memberships.list(user_id=user.id)
        return [
            AssociationRead(id=m.association.id, name=m.association.name, role=cast(Role, m.role))
            for m in memberships
        ]

    async def create(self, user: User, name: str) -> AssociationRead:
        association = await self.associations.add(Association(name=name))
        await self.memberships.add(
            Membership(user_id=user.id, association_id=association.id, role="manager")
        )
        return AssociationRead(id=association.id, name=association.name, role="manager")

    async def detail(self, user: User, association_id: UUID) -> AssociationDetail:
        own = await self._membership_of(user, association_id)
        members = await self.memberships.list(association_id=association_id)
        return AssociationDetail(
            id=own.association.id,
            name=own.association.name,
            role=cast(Role, own.role),
            members=[member_read(m) for m in members],
        )

    async def add_member(
        self, manager: User, association_id: UUID, display_name: str, email: str, role: Role
    ) -> MemberRead:
        await self._manager_of(manager, association_id)
        user = await self.users.get_one_or_none(email=email.lower())
        if user is None:
            user = await self.users.add(
                User(display_name=display_name, email=email.lower(), password_hash=None)
            )
        elif await self.memberships.exists(user_id=user.id, association_id=association_id):
            raise ConflictException(f"{user.display_name} is already a member.")
        membership = await self.memberships.add(
            Membership(user_id=user.id, association_id=association_id, role=role),
            auto_refresh=True,
        )
        return member_read(membership)

    async def change_role(
        self, manager: User, association_id: UUID, user_id: UUID, role: Role
    ) -> MemberRead:
        await self._manager_of(manager, association_id)
        membership = await self.memberships.get_one_or_none(
            user_id=user_id, association_id=association_id
        )
        if membership is None:
            raise NotFoundException("Not a member of this association.")
        if membership.role == "manager" and role == "volunteer":
            managers = await self.memberships.count(association_id=association_id, role="manager")
            if managers == 1:
                raise ConflictException("An association keeps at least one manager.")
        membership.role = role
        return member_read(await self.memberships.update(membership))

    async def _membership_of(self, user: User, association_id: UUID) -> Membership:
        membership = await self.memberships.get_one_or_none(
            user_id=user.id, association_id=association_id
        )
        if membership is None:
            raise NotFoundException("Association not found.")
        return membership

    async def _manager_of(self, user: User, association_id: UUID) -> Membership:
        membership = await self._membership_of(user, association_id)
        if membership.role != "manager":
            raise PermissionDeniedException("Only managers can do this.")
        return membership
