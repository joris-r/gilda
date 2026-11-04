import logging
import os
import secrets
from collections.abc import Awaitable, Callable, Sequence
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
    ServiceUnavailableException,
)
from litestar.status_codes import HTTP_409_CONFLICT
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import (
    AccessLink,
    Association,
    EmailVerificationToken,
    Membership,
    PasswordResetToken,
    Role,
    User,
)
from gilda.core.repositories import (
    AccessLinkRepository,
    AssociationRepository,
    EmailVerificationTokenRepository,
    MembershipRepository,
    PasswordResetTokenRepository,
    UserRepository,
)
from gilda.core.schemas import AssociationDetail, AssociationRead, MemberRead
from gilda.mailer import (
    EmailNotSentError,
    Language,
    send_access_link_email,
    send_password_reset_email,
    send_verification_email,
)

_logger = logging.getLogger(__name__)
_hasher = PasswordHasher()
TOKEN_LIFETIME = timedelta(hours=24)
RESET_TOKEN_LIFETIME = timedelta(hours=1)


def is_superuser_email(email: str) -> bool:
    superuser_email = os.environ.get("SUPERUSER_EMAIL")
    return superuser_email is not None and superuser_email.lower() == email.lower()


def is_superuser(user: User) -> bool:
    return user.email is not None and is_superuser_email(user.email)


def invitation_only() -> bool:
    return os.environ.get("INVITATION_ONLY") == "true"


class ConflictException(ClientException):
    status_code = HTTP_409_CONFLICT


# What another domain does when a user's membership of an association ends (R28).
MembershipEndHook = Callable[[AsyncSession, Association, UUID], Awaitable[None]]


async def end_membership(
    db_session: AsyncSession, membership: Membership, hooks: Sequence[MembershipEndHook]
) -> None:
    for hook in hooks:
        await hook(db_session, membership.association, membership.user_id)
    await MembershipRepository(session=db_session).delete(membership.id)


def member_read(membership: Membership, access_link: bool) -> MemberRead:
    user = membership.user
    return MemberRead(
        user_id=user.id,
        display_name=user.display_name,
        email=user.address,
        has_account=user.has_account,
        email_verified=user.email_verified,
        access_link=access_link,
        role=cast(Role, membership.role),
    )


class AccountService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.users = UserRepository(session=db_session)
        self.tokens = EmailVerificationTokenRepository(session=db_session)
        self.reset_tokens = PasswordResetTokenRepository(session=db_session)
        self.access_links = AccessLinkRepository(session=db_session)

    async def find_by_email(self, email: str) -> User | None:
        return await self.users.get_one_or_none(email=email.lower())

    async def create_account(
        self, display_name: str, email: str, password: str, language: Language
    ) -> User:
        password_hash = _hasher.hash(password)
        user = await self.find_by_email(email)
        if user is None:
            if invitation_only() and not is_superuser_email(email):
                raise PermissionDeniedException("This email has not been invited.")
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
        try:
            await self._issue_token(user, language)
        except EmailNotSentError as error:
            # R10: an error response rolls the transaction back, so nothing is saved.
            raise ServiceUnavailableException(
                "The confirmation email could not be sent. Try again later."
            ) from error
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

    async def get_active(self, user_id: UUID) -> User | None:
        """The user, unless their account is deleted: its sessions no longer authenticate."""
        user = await self.get(user_id)
        return None if user is None or user.deleted_at is not None else user

    async def delete_account(self, user: User, hooks: Sequence[MembershipEndHook]) -> None:
        memberships = MembershipRepository(session=self.db_session)
        for membership in await memberships.list(user_id=user.id):
            if membership.role == "manager":
                await promote_if_last_manager(memberships, membership)
            await end_membership(self.db_session, membership, hooks)
        await self.tokens.delete_where(user_id=user.id)
        await self.reset_tokens.delete_where(user_id=user.id)
        await self.access_links.delete_where(user_id=user.id)
        user.email = None
        user.password_hash = None
        user.deleted_at = datetime.now(UTC)
        await self.users.update(user)

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

    async def resend_confirmation(self, email: str, language: Language) -> None:
        user = await self.find_by_email(email)
        if user is not None and not user.email_verified:
            try:
                await self._issue_token(user, language)
            except EmailNotSentError:
                # Still 204: an error here would reveal that the email has a pending account.
                _logger.exception("Resending the confirmation email failed")

    async def request_password_reset(self, email: str, language: Language) -> None:
        user = await self.find_by_email(email)
        if user is None or not user.has_account:
            return
        existing = await self.reset_tokens.get_one_or_none(user_id=user.id)
        if existing is not None:
            await self.reset_tokens.delete(existing.id)
        token = await self.reset_tokens.add(
            PasswordResetToken(
                user_id=user.id,
                token=secrets.token_urlsafe(32),
                expires_at=datetime.now(UTC) + RESET_TOKEN_LIFETIME,
            )
        )
        try:
            send_password_reset_email(user.address, token.token, language)
        except EmailNotSentError:
            # Still 204: an error here would reveal that the email has an account.
            _logger.exception("Sending the password reset email failed")

    async def reset_password(self, token: str, password: str) -> User:
        record = await self.reset_tokens.get_one_or_none(token=token)
        if record is None or record.expires_at < datetime.now(UTC):
            raise NotFoundException("This reset link is unknown or expired.")
        user = await self.get(record.user_id)
        assert user is not None  # the foreign key guarantees it
        user.password_hash = _hasher.hash(password)
        if user.email_verified_at is None:
            # The link reached the user's mailbox, which proves the email.
            user.email_verified_at = datetime.now(UTC)
        await self.users.update(user)
        await self.reset_tokens.delete(record.id)
        return user

    async def send_access_link(self, email: str, language: Language) -> None:
        user = await self.find_by_email(email)
        if user is None:
            return
        try:
            await send_access_link(self.access_links, user, language)
        except EmailNotSentError:
            # Still 204: an error here would reveal that the email is known.
            _logger.exception("Sending the access link email failed")

    async def sign_in_with_link(self, token: str) -> tuple[User, AccessLink]:
        link = await self.access_links.get_one_or_none(token=token)
        if link is None:
            raise NotFoundException("This link is unknown or revoked.")
        user = await self.get(link.user_id)
        assert user is not None  # the foreign key guarantees it
        if user.email_verified_at is None:
            # The link reached the user's mailbox, which proves the email.
            user.email_verified_at = datetime.now(UTC)
            await self.users.update(user)
        return user, link

    async def link_exists(self, link_id: UUID) -> bool:
        return await self.access_links.exists(id=link_id)

    async def revoke_link(self, user_id: UUID) -> None:
        await revoke_access_link(self.access_links, user_id)

    async def _issue_token(self, user: User, language: Language) -> None:
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
        send_verification_email(user.address, token.token, language)


async def promote_if_last_manager(memberships: MembershipRepository, leaving: Membership) -> None:
    """R30: when the only manager leaves, every remaining member becomes a manager."""
    others = [
        m
        for m in await memberships.list(association_id=leaving.association_id)
        if m.id != leaving.id
    ]
    if any(m.role == "manager" for m in others):
        return
    for member in others:
        member.role = "manager"
        await memberships.update(member)


async def send_access_link(links: AccessLinkRepository, user: User, language: Language) -> None:
    # R25: the same link until it is revoked, so older emails keep working.
    link = await links.get_one_or_none(user_id=user.id)
    if link is None:
        link = await links.add(AccessLink(user_id=user.id, token=secrets.token_urlsafe(32)))
    send_access_link_email(user.address, link.token, language)


async def revoke_access_link(links: AccessLinkRepository, user_id: UUID) -> None:
    # R23: sessions opened by the link check it still exists (see provide_current_user).
    link = await links.get_one_or_none(user_id=user_id)
    if link is not None:
        await links.delete(link.id)


class AssociationService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.users = UserRepository(session=db_session)
        self.associations = AssociationRepository(session=db_session)
        self.memberships = MembershipRepository(session=db_session)
        self.access_links = AccessLinkRepository(session=db_session)

    async def create(self, user: User, name: str) -> AssociationRead:
        association = await self.associations.add(Association(name=name))
        await self.memberships.add(
            Membership(user_id=user.id, association_id=association.id, role="manager")
        )
        return AssociationRead(id=association.id, name=association.name, role="manager")

    async def detail(self, user: User, association_id: UUID) -> AssociationDetail:
        own = await self._membership_of(user, association_id)
        members = await self.memberships.list(association_id=association_id)
        user_ids = [m.user_id for m in members]
        with_link = {
            link.user_id for link in await self.access_links.list(AccessLink.user_id.in_(user_ids))
        }
        return AssociationDetail(
            id=own.association.id,
            name=own.association.name,
            timezone=own.association.timezone,
            role=cast(Role, own.role),
            members=[member_read(m, m.user_id in with_link) for m in members],
        )

    async def rename(self, manager: User, association_id: UUID, name: str) -> AssociationRead:
        own = await self._manager_of(manager, association_id)
        own.association.name = name
        association = await self.associations.update(own.association)
        return AssociationRead(id=association.id, name=association.name, role="manager")

    async def delete(self, manager: User, association_id: UUID) -> None:
        await self._manager_of(manager, association_id)
        # What the association holds goes with it, by the foreign keys' ON DELETE CASCADE.
        await self.associations.delete(association_id)

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
        return await self._member_read(membership)

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
        return await self._member_read(await self.memberships.update(membership))

    async def send_member_link(
        self, manager: User, association_id: UUID, user_id: UUID, language: Language
    ) -> MemberRead:
        await self._manager_of(manager, association_id)
        membership = await self.memberships.get_one_or_none(
            user_id=user_id, association_id=association_id
        )
        if membership is None:
            raise NotFoundException("Not a member of this association.")
        try:
            await send_access_link(self.access_links, membership.user, language)
        except EmailNotSentError as error:
            # An error response rolls the transaction back, so no link is created.
            raise ServiceUnavailableException(
                "The sign-in link could not be sent. Try again later."
            ) from error
        return await self._member_read(membership)

    async def remove_member(
        self,
        manager: User,
        association_id: UUID,
        user_id: UUID,
        hooks: Sequence[MembershipEndHook],
    ) -> None:
        await self._manager_of(manager, association_id)
        membership = await self.memberships.get_one_or_none(
            user_id=user_id, association_id=association_id
        )
        if membership is None:
            raise NotFoundException("Not a member of this association.")
        if membership.role == "manager":
            managers = await self.memberships.count(association_id=association_id, role="manager")
            if managers == 1:
                raise ConflictException("An association keeps at least one manager.")
        await end_membership(self.db_session, membership, hooks)

    async def revoke_member_link(self, manager: User, association_id: UUID, user_id: UUID) -> None:
        await self._manager_of(manager, association_id)
        if not await self.memberships.exists(user_id=user_id, association_id=association_id):
            raise NotFoundException("Not a member of this association.")
        await revoke_access_link(self.access_links, user_id)

    async def _member_read(self, membership: Membership) -> MemberRead:
        return member_read(membership, await self.access_links.exists(user_id=membership.user_id))

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
