import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest

from tests.core.conftest import (
    ask_for_link,
    create_association,
    latest_access_token,
    open_link,
    run_sql,
    shown,
    sign_in,
    sign_up,
    signed_in_as,
    unique_email,
    unique_slug,
)


def hold(
    server: Any,
    client: Any,
    path: str,
    signals: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Callable[[], httpx.Response]:
    """Sends a POST of `client`'s browser that has loaded its session once this returns, its
    body held back. The function returned lets it finish, gives the browser the cookies its
    response sets, and returns that response."""
    loaded = asyncio.Event()
    release = asyncio.Event()

    async def body() -> AsyncIterator[bytes]:
        loaded.set()
        await release.wait()
        yield json.dumps(signals).encode()

    async def send() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=server.app),
            base_url=str(client.base_url),
            cookies=client.cookies,
        ) as browser:
            return await browser.post(
                path,
                content=body(),
                headers={"content-type": "application/json", **(headers or {})},
            )

    async def until_loaded() -> None:
        await asyncio.wait_for(loaded.wait(), 10)

    portal = server.blocking_portal
    future = portal.start_task_soon(send)
    try:
        portal.call(until_loaded)
    except TimeoutError:
        portal.call(release.set)
        raise

    def finish() -> httpx.Response:
        portal.call(release.set)
        response: httpx.Response = future.result(timeout=10)
        client.cookies.extract_cookies(response)
        return response

    return finish


def hold_unchanging(server: Any, client: Any) -> Callable[[], None]:
    """Holds a request that changes nothing in its session: a Sign in refused. The function
    returned lets it finish, and checks that it was answered."""
    finish = hold(server, client, "/sign-in", {"email": unique_email("Nobody"), "password": "x"})

    def finished() -> None:
        assert "window.location" not in shown(finish())

    return finished


def hold_changing(server: Any, client: Any) -> Callable[[], None]:
    """Holds a request that changes its session: Change identifier, which keeps a notice for
    its tab, on an association the signed-in user creates first. The function returned lets it
    finish, and checks that it succeeded."""
    association = create_association(client)
    new_slug = unique_slug()
    finish = hold(
        server,
        client,
        f"/association/{association['slug']}/identifier",
        {"slug": new_slug},
        headers={"X-Tab": "tab-1"},
    )

    def finished() -> None:
        assert f"/association/{new_slug}" in shown(finish())

    return finished


HOLDERS = pytest.mark.parametrize("holder", [hold_unchanging, hold_changing])


def stored(session_id: str) -> bool:
    """Whether a session with this id is stored."""
    count = run_sql("SELECT count(*) FROM user_session WHERE session_id = :id", id=session_id)
    return bool(count)


def claim(client: Any, tab: str) -> str:
    """What GET /notice gives the tab `tab`, as the page asks it; empty when it patches
    nothing."""
    response = client.get("/notice", headers={"X-Tab": tab})
    assert response.status_code in (200, 204), response.text
    return shown(response) if response.status_code == 200 else ""


class TestStaysDeleted:
    # /core/operations/general/stays-deleted
    # /core/operations/sign-out/signed-out
    @HOLDERS
    def test_sign_out_holds_while_a_request_of_the_session_is_in_flight(
        self, server: Any, client: Any, holder: Callable[[Any, Any], Callable[[], None]]
    ) -> None:
        sign_up(client, "Alice")
        session_id = client.cookies["session"]
        finish = holder(server, client)

        assert client.post("/sign-out").status_code == 200
        finish()

        assert not stored(session_id)
        assert signed_in_as(client) is None

    # /core/operations/general/stays-deleted
    # /core/operations/sign-in/new-session
    @HOLDERS
    def test_signing_in_holds_while_a_request_of_the_former_session_is_in_flight(
        self,
        server: Any,
        client: Any,
        new_client: Callable[[], Any],
        holder: Callable[[Any, Any], Callable[[], None]],
    ) -> None:
        bob = sign_up(new_client(), "Bob")
        sign_up(client, "Alice")
        former = client.cookies["session"]
        finish = holder(server, client)

        assert "window.location" in shown(sign_in(client, bob["email"]))
        finish()

        assert not stored(former)
        assert signed_in_as(client) == "Bob"

    # /core/operations/general/stays-deleted
    # /core/operations/revoke-my-access-link/revoked
    @HOLDERS
    def test_revoking_the_link_holds_while_a_request_of_a_session_it_opened_is_in_flight(
        self,
        server: Any,
        client: Any,
        new_client: Callable[[], Any],
        holder: Callable[[Any, Any], Callable[[], None]],
    ) -> None:
        alice = sign_up(client, "Alice")
        ask_for_link(client, alice["email"])
        by_link = new_client()
        assert open_link(by_link, latest_access_token(alice["email"])).status_code == 200
        session_id = by_link.cookies["session"]
        finish = holder(server, by_link)

        assert client.post("/revoke-access-link").status_code == 200
        finish()

        assert not stored(session_id)
        assert signed_in_as(by_link) is None

    # /core/operations/general/stays-deleted
    # /core/operations/delete-account/deleted
    def test_deleting_the_account_holds_while_a_request_of_its_session_is_in_flight(
        self, server: Any, client: Any
    ) -> None:
        sign_up(client, "Alice")
        session_id = client.cookies["session"]
        finish = hold_unchanging(server, client)

        assert client.post("/delete-account").status_code == 200
        finish()

        assert not stored(session_id)
        assert signed_in_as(client) is None


class TestNoticeWithRequestsInFlight:
    # /ui/notices/led
    def test_a_claimed_notice_stays_claimed_after_a_request_loaded_before_the_claim(
        self, server: Any, client: Any
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        new_slug = unique_slug()
        response = client.post(
            f"/association/{association['slug']}/identifier",
            json={"slug": new_slug},
            headers={"X-Tab": "tab-1"},
        )
        assert f"/association/{new_slug}" in shown(response)
        finish = hold_unchanging(server, client)

        assert new_slug in claim(client, "tab-1")
        finish()

        # Every screen of the tab, once it opens, claims the tab's notice so.
        assert new_slug not in claim(client, "tab-1")

    # /ui/notices/led
    def test_a_notice_stays_kept_after_a_request_loaded_before_the_action(
        self, server: Any, client: Any
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        new_slug = unique_slug()
        finish = hold_unchanging(server, client)

        response = client.post(
            f"/association/{association['slug']}/identifier",
            json={"slug": new_slug},
            headers={"X-Tab": "tab-1"},
        )
        assert f"/association/{new_slug}" in shown(response)
        finish()

        assert new_slug in claim(client, "tab-1")
