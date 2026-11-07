import re
from typing import Any
from uuid import UUID

from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.services import AssociationService
from gilda.core.sessions import find_current_user
from gilda.home.services import HomeService
from gilda.planning.schemas import Status
from gilda.planning.services import PlanningService
from gilda.web.rendering import fragment, interface_language, page, translate

_REFUSALS = (ClientException, NotFoundException, PermissionDeniedException)


@get("/")
async def home(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    associations = await HomeService(db_session).list_for(user)
    return page(request, "my_associations.html", user=user, associations=associations)


async def _status_changed(
    request: Request[Any, Any, Any],
    db_session: AsyncSession,
    slug: str,
    registration_id: str,
    status: Status,
) -> DatastarResponse:
    """Confirms or cancels one of the user's registrations (R7), then shows the association as
    My associations now lists it."""
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        try:
            registration = UUID(registration_id)
        except ValueError as invalid:
            raise NotFoundException("Registration not found.") from invalid
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).change_status(user, association.id, registration, status)
    except _REFUSALS:
        message = translate(interface_language(request), "error")
        error = fragment(
            request, "form_error.html", message=message, error_id=f"summary-error-{slug}"
        )
        return DatastarResponse(ServerSentEventGenerator.patch_elements(error))
    shown = await HomeService(db_session).one_for(user, association.id)
    item = fragment(request, "my_associations_item.html", association=shown)
    # On one line, so that each line of the summary stays whole in the event.
    return DatastarResponse(ServerSentEventGenerator.patch_elements(re.sub(r"\s*\n\s*", " ", item)))


@post("/association/{slug:str}/summary/{registration_id:str}/confirm", status_code=200)
async def confirm_on_summary(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    registration_id: str,
) -> DatastarResponse:
    return await _status_changed(request, db_session, slug, registration_id, "confirmed")


@post("/association/{slug:str}/summary/{registration_id:str}/cancel", status_code=200)
async def ok_on_summary(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    registration_id: str,
) -> DatastarResponse:
    return await _status_changed(request, db_session, slug, registration_id, "cancelled")
