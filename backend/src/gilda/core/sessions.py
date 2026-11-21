from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from advanced_alchemy.extensions.litestar.session import (
    SESSION_ID_MAX_LENGTH,
    SQLAlchemyAsyncSessionBackend,
)
from litestar import Request
from litestar.connection import ASGIConnection
from litestar.datastructures import Cookie, MutableScopeHeaders
from litestar.types import Empty, Message, ScopeSession
from litestar.utils.dataclass import extract_dataclass_items
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import SESSION_LINK_KEY, SESSION_USER_KEY, AccessLink, User
from gilda.core.services import AccountService

_NEW_SESSION_ID = "new_session_id"
_LOADED_SESSION = "loaded_session"
_COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def set_session_with_new_id(request: Request[Any, Any, Any], data: dict[str, Any]) -> None:
    """Sets the session, stored under a new ID once the response is sent."""
    request.set_session(data)
    request.state[_NEW_SESSION_ID] = True


class SessionBackend(SQLAlchemyAsyncSessionBackend):
    """Stores a session only when its request changed it, and never stores again one deleted
    while the request ran; Litestar would save back the copy each request loaded, by an upsert.
    It also replaces the session ID on sign-in, which Litestar keeps from the incoming cookie."""

    async def load_from_connection(
        self, connection: ASGIConnection[Any, Any, Any, Any]
    ) -> dict[str, Any]:
        data = await super().load_from_connection(connection)
        serialized = self.serialize_data(data, connection.scope) if data else None
        connection.state[_LOADED_SESSION] = serialized
        return data

    async def store_in_message(
        self,
        scope_session: ScopeSession,
        message: Message,
        connection: ASGIConnection[Any, Any, Any, Any],
    ) -> None:
        store = self.config.get_store_from_app(connection.scope["app"])
        headers = MutableScopeHeaders.from_message(message)
        cookie_id = connection.cookies.get(self.config.key)
        loaded = connection.state.get(_LOADED_SESSION)

        if scope_session is Empty:
            if cookie_id:
                await self.delete(cookie_id, store=store)
                headers.add("Set-Cookie", self._cookie("null", max_age=0))
            return
        new_id = connection.state.get(_NEW_SESSION_ID) is True
        data = self.serialize_data(scope_session, connection.scope)
        if new_id and cookie_id:
            await self.delete(cookie_id, store=store)
        if not new_id and data == (loaded or self.serialize_data({})):
            return
        if not new_id and loaded is not None and cookie_id:
            if await self._update(cookie_id, data):
                headers.add("Set-Cookie", self._cookie(cookie_id))
            return
        session_id = self.generate_session_id()
        await self.set(session_id, data, store=store)
        headers.add("Set-Cookie", self._cookie(session_id))

    async def _update(self, session_id: str, data: bytes) -> bool:
        """Replaces the data of a stored session; whether it was still stored."""
        expires_at = datetime.now(UTC) + timedelta(seconds=self.config.max_age)
        statement = (
            update(self.model)
            .where(self.model.session_id == session_id[:SESSION_ID_MAX_LENGTH])
            .values(data=data, expires_at=expires_at)
            .returning(self.model.session_id)
        )
        async with self.alchemy.get_session() as db_session:
            updated = (await db_session.execute(statement)).scalar_one_or_none()
            await db_session.commit()
        return updated is not None

    def _cookie(self, value: str, max_age: int = _COOKIE_MAX_AGE) -> str:
        params = dict(
            extract_dataclass_items(self.config, exclude_none=True, include=Cookie.__dict__.keys())
        )
        params["max_age"] = max_age
        return Cookie(value=value, key=self.config.key, **params).to_header(header="")


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
