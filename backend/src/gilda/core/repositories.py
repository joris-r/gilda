from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from gilda.core.models import Association, EmailVerificationToken, Membership, User


class UserRepository(SQLAlchemyAsyncRepository[User]):
    model_type = User


class EmailVerificationTokenRepository(SQLAlchemyAsyncRepository[EmailVerificationToken]):
    model_type = EmailVerificationToken


class AssociationRepository(SQLAlchemyAsyncRepository[Association]):
    model_type = Association


class MembershipRepository(SQLAlchemyAsyncRepository[Membership]):
    model_type = Membership
