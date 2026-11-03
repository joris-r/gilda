from typing import Any
from uuid import UUID

from litestar import Controller, Request, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotAuthorizedException
from litestar.params import FromPath, JSONBody
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import AccessLink, User
from gilda.core.schemas import (
    AccessLinkRequest,
    AccessLinkSignIn,
    AccountCreate,
    AssociationCreate,
    AssociationDetail,
    AssociationRead,
    Credentials,
    MemberCreate,
    MemberRead,
    MemberUpdate,
    PasswordResetConfirm,
    PasswordResetRequest,
    ResendRequest,
    SessionRead,
    UserRead,
    VerifyRequest,
)
from gilda.core.services import (
    AccountService,
    AssociationService,
    MembershipEndHook,
    is_superuser,
)
from gilda.core.sessions import set_session_with_new_id
from gilda.mailer import Language, preferred_language

SESSION_USER_KEY = "user_id"
SESSION_LINK_KEY = "access_link_id"


def email_language(request: Request[Any, Any, Any]) -> Language:
    return preferred_language(request.headers.get("accept-language"))


def user_read(user: User) -> UserRead:
    return UserRead(id=user.id, display_name=user.display_name, email=user.address)


def session_read(user: User) -> SessionRead:
    return SessionRead(
        id=user.id,
        display_name=user.display_name,
        email=user.address,
        superuser=is_superuser(user),
    )


def sign_in_as(
    request: Request[Any, Any, Any], user: User, access_link: AccessLink | None = None
) -> SessionRead:
    session = {SESSION_USER_KEY: str(user.id)}
    if access_link is not None:
        session[SESSION_LINK_KEY] = str(access_link.id)
    set_session_with_new_id(request, session)
    return session_read(user)


async def provide_current_user(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> User:
    session = request.session or {}
    accounts = AccountService(db_session)
    user_id = session.get(SESSION_USER_KEY)
    user = await accounts.get_active(UUID(user_id)) if user_id else None
    link_id = session.get(SESSION_LINK_KEY)
    if link_id and not await accounts.link_exists(UUID(link_id)):
        user = None
    if user is None:
        raise NotAuthorizedException("Not signed in.")
    return user


class AccountController(Controller):
    @post("/accounts")
    async def create_account(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[AccountCreate],
    ) -> UserRead:
        user = await AccountService(db_session).create_account(
            data.display_name, data.email, data.password, email_language(request)
        )
        return user_read(user)

    @delete("/accounts/me", dependencies={"current_user": Provide(provide_current_user)})
    async def delete_account(
        self,
        request: Request[Any, Any, Any],
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        membership_end_hooks: NamedDependency[list[MembershipEndHook]],
    ) -> None:
        await AccountService(db_session).delete_account(current_user, membership_end_hooks)
        request.clear_session()

    @post("/accounts/verify", status_code=200)
    async def verify_email(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[VerifyRequest],
    ) -> SessionRead:
        user = await AccountService(db_session).confirm(data.token)
        return sign_in_as(request, user)

    @post("/accounts/verify/resend", status_code=204)
    async def resend_verification(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[ResendRequest],
    ) -> None:
        await AccountService(db_session).resend_confirmation(data.email, email_language(request))

    @post("/accounts/password-reset", status_code=204)
    async def request_password_reset(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[PasswordResetRequest],
    ) -> None:
        await AccountService(db_session).request_password_reset(data.email, email_language(request))

    @post("/accounts/password-reset/confirm", status_code=200)
    async def reset_password(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[PasswordResetConfirm],
    ) -> SessionRead:
        user = await AccountService(db_session).reset_password(data.token, data.password)
        return sign_in_as(request, user)

    @post("/session", status_code=200)
    async def sign_in(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[Credentials],
    ) -> SessionRead:
        user = await AccountService(db_session).authenticate(data.email, data.password)
        return sign_in_as(request, user)

    @post("/access-link", status_code=204)
    async def send_access_link(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[AccessLinkRequest],
    ) -> None:
        await AccountService(db_session).send_access_link(data.email, email_language(request))

    @post("/session/access-link", status_code=200)
    async def sign_in_with_link(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[AccessLinkSignIn],
    ) -> SessionRead:
        user, link = await AccountService(db_session).sign_in_with_link(data.token)
        return sign_in_as(request, user, link)

    @delete("/access-link", dependencies={"current_user": Provide(provide_current_user)})
    async def revoke_access_link(
        self, current_user: NamedDependency[User], db_session: NamedDependency[AsyncSession]
    ) -> None:
        await AccountService(db_session).revoke_link(current_user.id)

    @get("/session", dependencies={"current_user": Provide(provide_current_user)})
    async def get_session(self, current_user: NamedDependency[User]) -> SessionRead:
        return session_read(current_user)

    @delete("/session")
    async def sign_out(self, request: Request[Any, Any, Any]) -> None:
        request.clear_session()


class AssociationController(Controller):
    path = "/associations"
    dependencies = {"current_user": Provide(provide_current_user)}  # noqa: RUF012

    @post()
    async def create_association(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[AssociationCreate],
    ) -> AssociationRead:
        return await AssociationService(db_session).create(current_user, data.name)

    @get("/{association_id:uuid}")
    async def get_association(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> AssociationDetail:
        return await AssociationService(db_session).detail(current_user, association_id)

    @post("/{association_id:uuid}/members")
    async def add_member(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        data: JSONBody[MemberCreate],
    ) -> MemberRead:
        return await AssociationService(db_session).add_member(
            current_user, association_id, data.display_name, data.email, data.role
        )

    @patch("/{association_id:uuid}/members/{user_id:uuid}")
    async def change_role(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        user_id: FromPath[UUID],
        data: JSONBody[MemberUpdate],
    ) -> MemberRead:
        return await AssociationService(db_session).change_role(
            current_user, association_id, user_id, data.role
        )

    @delete("/{association_id:uuid}/members/{user_id:uuid}")
    async def remove_member(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        membership_end_hooks: NamedDependency[list[MembershipEndHook]],
        association_id: FromPath[UUID],
        user_id: FromPath[UUID],
    ) -> None:
        await AssociationService(db_session).remove_member(
            current_user, association_id, user_id, membership_end_hooks
        )

    @post("/{association_id:uuid}/members/{user_id:uuid}/access-link", status_code=200)
    async def send_member_link(
        self,
        request: Request[Any, Any, Any],
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        user_id: FromPath[UUID],
    ) -> MemberRead:
        return await AssociationService(db_session).send_member_link(
            current_user, association_id, user_id, email_language(request)
        )

    @delete("/{association_id:uuid}/members/{user_id:uuid}/access-link")
    async def revoke_member_link(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        user_id: FromPath[UUID],
    ) -> None:
        await AssociationService(db_session).revoke_member_link(
            current_user, association_id, user_id
        )
