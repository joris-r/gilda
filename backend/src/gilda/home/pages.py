from typing import Any

from litestar import Request, get
from litestar.di import NamedDependency
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import find_current_user
from gilda.home.services import HomeService
from gilda.web.rendering import page


@get("/")
async def home(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    associations = await HomeService(db_session).list_for(user)
    return page(request, "my_associations.html", user=user, associations=associations)
