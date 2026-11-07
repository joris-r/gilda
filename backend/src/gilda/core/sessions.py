from typing import Any
from uuid import UUID

from advanced_alchemy.extensions.litestar.session import SQLAlchemyAsyncSessionBackend
from litestar import Request
from litestar.connection import ASGIConnection
from litestar.types import Message, ScopeSession
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import AccessLink, User
from gilda.core.services import AccountService

_NEW_SESSION_ID = "new_session_id"


def set_session_with_new_id(request: Request[Any, Any, Any], data: dict[str, Any]) -> None:
    """Sets the session, stored under a new ID once the response is sent."""
    request.set_session(data)
    request.state[_NEW_SESSION_ID] = True


class SessionBackend(SQLAlchemyAsyncSessionBackend):
    """Litestar keeps the incoming cookie's session ID; this one can replace it."""

    def get_session_id(self, connection: ASGIConnection[Any, Any, Any, Any]) -> str:
        new_id = connection.state.get(_NEW_SESSION_ID)
        return new_id if isinstance(new_id, str) else super().get_session_id(connection)

    async def store_in_message(
        self,
        scope_session: ScopeSession,
        message: Message,
        connection: ASGIConnection[Any, Any, Any, Any],
    ) -> None:
        if connection.state.get(_NEW_SESSION_ID) is True:
            if old_id := connection.cookies.get(self.config.key):
                store = self.config.get_store_from_app(connection.scope["app"])
                await self.delete(old_id, store=store)
            connection.state[_NEW_SESSION_ID] = self.generate_session_id()
        await super().store_in_message(scope_session, message, connection)


SESSION_USER_KEY = "user_id"
SESSION_LINK_KEY = "access_link_id"


def sign_in_as(
    request: Request[Any, Any, Any], user: User, access_link: AccessLink | None = None
) -> None:
    """Signs `user` in, under a new session ID (R16)."""
    session = {SESSION_USER_KEY: str(user.id)}
    if access_link is not None:
        session[SESSION_LINK_KEY] = str(access_link.id)
    set_session_with_new_id(request, session)


async def find_current_user(
    request: Request[Any, Any, Any], db_session: AsyncSession
) -> User | None:
    """The user signed in, or None; a session opened with a revoked link is signed out (R23)."""
    session = request.session or {}
    accounts = AccountService(db_session)
    user_id = session.get(SESSION_USER_KEY)
    user = await accounts.get_active(UUID(user_id)) if user_id else None
    link_id = session.get(SESSION_LINK_KEY)
    if link_id and not await accounts.link_exists(UUID(link_id)):
        return None
    return user
