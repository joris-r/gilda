from typing import Any
from uuid import UUID

from litestar import Controller, Request, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotAuthorizedException
from litestar.params import FromPath, JSONBody
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import User
from gilda.core.schemas import (
    AccountCreate,
    AssociationCreate,
    AssociationDetail,
    AssociationRead,
    Credentials,
    MemberCreate,
    MemberRead,
    MemberUpdate,
    UserRead,
)
from gilda.core.services import AccountService, AssociationService

SESSION_USER_KEY = "user_id"


def user_read(user: User) -> UserRead:
    return UserRead(id=user.id, display_name=user.display_name, email=user.email)


async def provide_current_user(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> User:
    user_id = request.session.get(SESSION_USER_KEY) if request.session else None
    user = await AccountService(db_session).get(UUID(user_id)) if user_id else None
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
            data.display_name, data.email, data.password
        )
        request.set_session({SESSION_USER_KEY: str(user.id)})
        return user_read(user)

    @post("/session", status_code=200)
    async def sign_in(
        self,
        request: Request[Any, Any, Any],
        db_session: NamedDependency[AsyncSession],
        data: JSONBody[Credentials],
    ) -> UserRead:
        user = await AccountService(db_session).authenticate(data.email, data.password)
        request.set_session({SESSION_USER_KEY: str(user.id)})
        return user_read(user)

    @get("/session", dependencies={"current_user": Provide(provide_current_user)})
    async def get_session(self, current_user: NamedDependency[User]) -> UserRead:
        return user_read(current_user)

    @delete("/session")
    async def sign_out(self, request: Request[Any, Any, Any]) -> None:
        request.clear_session()


class AssociationController(Controller):
    path = "/associations"
    dependencies = {"current_user": Provide(provide_current_user)}  # noqa: RUF012

    @get()
    async def list_associations(
        self, current_user: NamedDependency[User], db_session: NamedDependency[AsyncSession]
    ) -> list[AssociationRead]:
        return await AssociationService(db_session).list_for(current_user)

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
