from typing import Any

from advanced_alchemy.extensions.litestar.session import SQLAlchemyAsyncSessionBackend
from litestar import Request
from litestar.connection import ASGIConnection
from litestar.types import Message, ScopeSession

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
