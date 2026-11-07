from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    create_association,
    delete_association,
    names_listed,
    shown,
    sign_up,
    unique_email,
    unique_slug,
)

NAME = "Jardin partagé des Lilas"
MALFORMED = ["", "Jardin", "jardin lilas", "jardin_lilas", "-jardin", "jardin-", "jardín", "a" * 51]
WELL_FORMED = ["a", "7", "2-jardins", "jardin-des-lilas"]


def manager_and_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> tuple[dict[str, Any], Any, str]:
    """Alice manages an association; Bruno, signed in on his own client, volunteers in it."""
    sign_up(client, "Alice")
    association = create_association(client, NAME)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    sign_up(bruno, "Bruno", bruno_email)
    assert add_member(client, association["id"], "Bruno", bruno_email).status_code == 201
    return association, bruno, bruno_email


def post(client: Any, slug: str) -> Any:
    return client.post("/api/associations", json={"name": NAME, "slug": slug})


# POST /api/associations


def test_post_api_associations_returns_the_slug(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()

    response = post(client, slug)

    assert response.status_code == 201
    assert response.json()["slug"] == slug


def test_post_api_associations_400_when_the_slug_is_missing(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.post("/api/associations", json={"name": NAME})

    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.parametrize("slug", MALFORMED)
def test_post_api_associations_400_when_the_slug_is_malformed(client: Any, slug: str) -> None:
    sign_up(client, "Alice")

    response = post(client, slug)

    assert response.status_code == 400
    assert "error" in response.json()
    assert names_listed(client) == []


def test_post_api_associations_accepts_a_slug_of_50_characters(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug().ljust(50, "x")

    response = post(client, slug)

    assert response.status_code == 201
    assert response.json()["slug"] == slug


@pytest.mark.parametrize("slug", WELL_FORMED)
def test_post_api_associations_accepts_a_well_formed_slug(client: Any, slug: str) -> None:
    sign_up(client, "Alice")

    # These fixed slugs may be held already, by another test or an earlier run.
    assert post(client, slug).status_code in (201, 409)


def test_post_api_associations_409_when_the_slug_is_taken(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()
    create_association(client, NAME, slug)
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))

    response = post(other, slug)

    assert response.status_code == 409
    assert "error" in response.json()
    assert names_listed(other) == []


def test_post_api_associations_409_when_the_slug_is_new(client: Any) -> None:
    sign_up(client, "Alice")

    response = post(client, "new")

    assert response.status_code == 409
    assert "error" in response.json()
    assert names_listed(client) == []


def test_post_api_associations_accepts_the_slug_of_a_deleted_association(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()
    association = create_association(client, NAME, slug)
    assert "window.location" in shown(delete_association(client, association["slug"]))

    assert post(client, slug).status_code == 201


# GET /api/associations/{id}


def test_get_api_association_shows_the_slug(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()
    association = create_association(client, NAME, slug)

    assert client.get(f"/api/associations/{association['id']}").json()["slug"] == slug


# GET /api/associations/by-slug/{slug}


def test_get_by_slug_returns_what_get_by_id_returns(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, _ = manager_and_volunteer(client, new_client)

    for member in (client, bruno):
        response = member.get(f"/api/associations/by-slug/{association['slug']}")

        assert response.status_code == 200
        assert response.json() == member.get(f"/api/associations/{association['id']}").json()


def test_get_by_slug_401_when_signed_out(client: Any) -> None:
    response = client.get(f"/api/associations/by-slug/{unique_slug()}")

    assert response.status_code == 401
    assert "error" in response.json()


def test_get_by_slug_404_when_no_association_has_it(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.get(f"/api/associations/by-slug/{unique_slug()}")

    assert response.status_code == 404
    assert "error" in response.json()


def test_get_by_slug_404_when_not_a_member(client: Any, new_client: Callable[[], Any]) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))

    response = other.get(f"/api/associations/by-slug/{association['slug']}")

    assert response.status_code == 404
    assert "error" in response.json()
