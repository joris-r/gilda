from datetime import UTC, date, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from litestar.connection import ASGIConnection


class Clock:
    """The current time, which the backend's code reads only from here.

    The application holds one, given when it is built; a subclass may answer another time.
    """

    def now(self) -> datetime:
        """The current instant, in UTC."""
        return datetime.now(UTC)

    def today(self, timezone: str) -> date:
        """The current date in `timezone`."""
        return self.now().astimezone(ZoneInfo(timezone)).date()


def clock_of(connection: ASGIConnection[Any, Any, Any, Any]) -> Clock:
    """The clock of the application serving `connection`."""
    return cast(Clock, connection.app.state.clock)
