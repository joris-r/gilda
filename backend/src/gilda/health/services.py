from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


async def database_is_reachable(db_session: AsyncSession) -> bool:
    try:
        await db_session.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError):
        return False
    return True
