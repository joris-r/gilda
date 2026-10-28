from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from gilda.core.models import Association, Membership, User


class UserRepository(SQLAlchemyAsyncRepository[User]):
    model_type = User


class AssociationRepository(SQLAlchemyAsyncRepository[Association]):
    model_type = Association


class MembershipRepository(SQLAlchemyAsyncRepository[Membership]):
    model_type = Membership
