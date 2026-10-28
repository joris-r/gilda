import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    PASSWORD,
    add_member,
    create_association,
    sign_up,
    unique_email,
)

# POST /api/accounts


def test_post_api_accounts_creates_the_account_and_signs_it_in(client: Any) -> None:
    email = unique_email("Alice")

    response = client.post(
        "/api/accounts",
        json={"display_name": "Alice", "email": email, "password": PASSWORD},
    )

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body == {"id": body["id"], "display_name": "Alice", "email": email}
    assert "session" in response.headers.get("set-cookie", "")
    assert client.get("/api/session").json() == body


def test_post_api_accounts_user_ids_are_uuids(client: Any) -> None:
    user = sign_up(client, "Alice")

    uuid.UUID(user["id"])


def test_r2_sign_up_takes_over_a_user_without_password(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    chloe_email = unique_email("Chloe")
    member = add_member(client, association["id"], "Chloé", chloe_email).json()

    chloe = new_client()
    response = chloe.post(
        "/api/accounts",
        json={"display_name": "Chloé L.", "email": chloe_email, "password": PASSWORD},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": member["user_id"],
        "display_name": "Chloé L.",
        "email": chloe_email,
    }
    assert chloe.get("/api/associations").json() == [
        {"id": association["id"], "name": association["name"], "role": "volunteer"}
    ]
    members = client.get(f"/api/associations/{association['id']}").json()["members"]
    chloe_member = next(m for m in members if m["user_id"] == member["user_id"])
    assert chloe_member["has_account"] is True
    assert chloe_member["display_name"] == "Chloé L."


def test_post_api_accounts_409_when_the_email_has_an_account(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = new_client().post(
        "/api/accounts",
        json={"display_name": "Other", "email": email, "password": PASSWORD},
    )

    assert response.status_code == 409
    assert "error" in response.json()


def test_post_api_accounts_409_when_the_email_differs_only_by_case(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = new_client().post(
        "/api/accounts",
        json={"display_name": "Other", "email": email.upper(), "password": PASSWORD},
    )

    assert response.status_code == 409


def test_post_api_accounts_400_when_the_password_has_fewer_than_8_characters(
    client: Any,
) -> None:
    response = client.post(
        "/api/accounts",
        json={"display_name": "Alice", "email": unique_email("Alice"), "password": "1234567"},
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_post_api_accounts_accepts_a_password_of_8_characters(client: Any) -> None:
    response = client.post(
        "/api/accounts",
        json={"display_name": "Alice", "email": unique_email("Alice"), "password": "12345678"},
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {"email": "missing-name@example.org", "password": PASSWORD},
        {"display_name": "", "email": "empty-name@example.org", "password": PASSWORD},
        {"display_name": "Alice", "password": PASSWORD},
        {"display_name": "Alice", "email": "not-an-email", "password": PASSWORD},
        {"display_name": "Alice", "email": "missing-password@example.org"},
    ],
)
def test_post_api_accounts_400_when_a_field_is_missing_empty_or_invalid(
    client: Any, body: dict[str, str]
) -> None:
    response = client.post("/api/accounts", json=body)

    assert response.status_code == 400
    assert "error" in response.json()


def test_post_api_accounts_400_when_the_body_is_not_json(client: Any) -> None:
    response = client.post(
        "/api/accounts", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 400
    assert "error" in response.json()


# POST /api/session


def test_post_api_session_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    user = sign_up(client, "Alice", email)
    browser = new_client()

    response = browser.post("/api/session", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json() == user
    assert "session" in response.headers.get("set-cookie", "")
    assert browser.get("/api/session").json() == user


def test_post_api_session_ignores_the_case_of_the_email(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = new_client().post(
        "/api/session", json={"email": email.upper(), "password": PASSWORD}
    )

    assert response.status_code == 200


def test_post_api_session_401_does_not_say_which_credential_is_wrong(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    association = create_association(client)
    volunteer_email = unique_email("Chloe")
    add_member(client, association["id"], "Chloé", volunteer_email)
    browser = new_client()

    wrong_password = browser.post("/api/session", json={"email": email, "password": "nope-nope"})
    unknown_email = browser.post(
        "/api/session", json={"email": unique_email("Nobody"), "password": PASSWORD}
    )
    no_account = browser.post("/api/session", json={"email": volunteer_email, "password": PASSWORD})

    assert [r.status_code for r in (wrong_password, unknown_email, no_account)] == [401] * 3
    assert wrong_password.json() == unknown_email.json() == no_account.json()
    assert "error" in wrong_password.json()
    assert browser.get("/api/session").status_code == 401


# GET /api/session


def test_get_api_session_401_when_signed_out(client: Any) -> None:
    response = client.get("/api/session")

    assert response.status_code == 401
    assert "error" in response.json()


# DELETE /api/session


def test_delete_api_session_signs_out(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.delete("/api/session")

    assert response.status_code == 204
    assert client.get("/api/session").status_code == 401
    assert client.get("/api/associations").status_code == 401
