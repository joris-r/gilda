from uuid import UUID

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import (
    SESSION_LINK_KEY,
    AccessLink,
    Association,
    EmailVerificationToken,
    Membership,
    PasswordResetToken,
    User,
    UserSession,
)


class UserRepository(SQLAlchemyAsyncRepository[User]):
    model_type = User


class EmailVerificationTokenRepository(SQLAlchemyAsyncRepository[EmailVerificationToken]):
    model_type = EmailVerificationToken


class PasswordResetTokenRepository(SQLAlchemyAsyncRepository[PasswordResetToken]):
    model_type = PasswordResetToken


class AccessLinkRepository(SQLAlchemyAsyncRepository[AccessLink]):
    model_type = AccessLink

    async def delete_sessions_opened_by(self, link_id: UUID) -> None:
        """Deletes the sessions the link opened, committed at once on a connection of its own:
        the session backend stores a request's session on its own connection before the
        request commits, and would wait on a row the request's transaction deleted."""
        opened_by = func.convert_from(UserSession.data, "UTF8").cast(JSONB)
        statement = delete(UserSession).where(opened_by[SESSION_LINK_KEY].astext == str(link_id))
        async with AsyncSession(self.session.bind) as own:
            await own.execute(statement)
            await own.commit()


class AssociationRepository(SQLAlchemyAsyncRepository[Association]):
    model_type = Association


class MembershipRepository(SQLAlchemyAsyncRepository[Membership]):
    model_type = Membership
