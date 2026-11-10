from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    create_association,
    email_count,
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


def slug_of(client: Any, association: dict[str, Any]) -> str:
    slug: str = client.get(f"/api/associations/{association['id']}").json()["slug"]
    return slug


def post(client: Any, slug: str) -> Any:
    return client.post("/api/associations", json={"name": NAME, "slug": slug})


def patch(client: Any, association: dict[str, Any], slug: str) -> Any:
    return client.patch(f"/api/associations/{association['id']}", json={"slug": slug})


# POST /api/associations


# /core/operations/create-association/created
def test_post_api_associations_returns_the_slug(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()

    response = post(client, slug)

    assert response.status_code == 201
    assert response.json()["slug"] == slug


# /core/operations/general/malformed
def test_post_api_associations_400_when_the_slug_is_missing(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.post("/api/associations", json={"name": NAME})

    assert response.status_code == 400
    assert "error" in response.json()


# /core/operations/create-association/malformed-slug /core/model/association/slug-format
@pytest.mark.parametrize("slug", MALFORMED)
def test_post_api_associations_400_when_the_slug_is_malformed(client: Any, slug: str) -> None:
    sign_up(client, "Alice")

    response = post(client, slug)

    assert response.status_code == 400
    assert "error" in response.json()
    assert client.get("/api/associations").json() == []


# /core/operations/create-association/created /core/model/association/slug-format
def test_post_api_associations_accepts_a_slug_of_50_characters(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug().ljust(50, "x")

    response = post(client, slug)

    assert response.status_code == 201
    assert response.json()["slug"] == slug


# /core/operations/create-association/created /core/model/association/slug-format
@pytest.mark.parametrize("slug", WELL_FORMED)
def test_post_api_associations_accepts_a_well_formed_slug(client: Any, slug: str) -> None:
    sign_up(client, "Alice")

    # These fixed slugs may be held already, by another test or an earlier run.
    assert post(client, slug).status_code in (201, 409)


# /core/operations/create-association/taken /core/model/association/slug-unique
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
    assert other.get("/api/associations").json() == []


# /core/operations/create-association/taken /core/model/association/slug-unique
def test_post_api_associations_409_when_the_slug_is_new(client: Any) -> None:
    sign_up(client, "Alice")

    response = post(client, "new")

    assert response.status_code == 409
    assert "error" in response.json()
    assert client.get("/api/associations").json() == []


# /core/operations/create-association/created /core/operations/delete-association/deleted
def test_post_api_associations_accepts_the_slug_of_a_deleted_association(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()
    association = create_association(client, NAME, slug)
    deleted = client.delete(f"/api/associations/{association['id']}")
    assert deleted.status_code == 204

    assert post(client, slug).status_code == 201


# GET /api/associations and GET /api/associations/{id}


# /home/operations/list-my-associations/listed
def test_get_api_associations_shows_the_slug(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()
    create_association(client, NAME, slug)

    assert [a["slug"] for a in client.get("/api/associations").json()] == [slug]


# /core/operations/get-association/detail
def test_get_api_association_shows_the_slug(client: Any) -> None:
    sign_up(client, "Alice")
    slug = unique_slug()
    association = create_association(client, NAME, slug)

    assert client.get(f"/api/associations/{association['id']}").json()["slug"] == slug


# GET /api/associations/by-slug/{slug}


# /core/operations/get-association/by-slug
def test_get_by_slug_returns_what_get_by_id_returns(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, _ = manager_and_volunteer(client, new_client)

    for member in (client, bruno):
        response = member.get(f"/api/associations/by-slug/{association['slug']}")

        assert response.status_code == 200
        assert response.json() == member.get(f"/api/associations/{association['id']}").json()


# /core/operations/general/signed-out
def test_get_by_slug_401_when_signed_out(client: Any) -> None:
    response = client.get(f"/api/associations/by-slug/{unique_slug()}")

    assert response.status_code == 401
    assert "error" in response.json()


# /core/operations/general/unknown-association
def test_get_by_slug_404_when_no_association_has_it(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.get(f"/api/associations/by-slug/{unique_slug()}")

    assert response.status_code == 404
    assert "error" in response.json()


# /core/operations/general/unknown-association
def test_get_by_slug_404_when_not_a_member(client: Any, new_client: Callable[[], Any]) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))

    response = other.get(f"/api/associations/by-slug/{association['slug']}")

    assert response.status_code == 404
    assert "error" in response.json()


# PATCH /api/associations/{id}


# /core/operations/update-association/new-slug /core/operations/update-association/answer
def test_patch_api_association_changes_the_slug(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)
    slug = unique_slug()

    response = patch(client, association, slug)

    assert response.status_code == 200
    assert response.json() == {
        "id": association["id"],
        "name": NAME,
        "slug": slug,
        "role": "manager",
    }
    assert client.get(f"/api/associations/by-slug/{slug}").json()["id"] == association["id"]


# /core/operations/update-association/renamed /core/operations/update-association/new-slug
def test_patch_api_association_changes_the_name_and_the_slug(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)
    slug = unique_slug()

    response = client.patch(
        f"/api/associations/{association['id']}",
        json={"name": "Jardin des Lilas", "slug": slug},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Jardin des Lilas"
    assert response.json()["slug"] == slug


# /core/operations/update-association/renamed
def test_patch_api_association_changing_the_name_leaves_the_slug_unchanged(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)

    response = client.patch(
        f"/api/associations/{association['id']}", json={"name": "Jardin des Lilas"}
    )

    assert response.status_code == 200
    assert response.json()["slug"] == association["slug"]
    found = client.get(f"/api/associations/by-slug/{association['slug']}")
    assert found.json()["name"] == "Jardin des Lilas"


# /core/operations/update-association/new-slug
def test_patch_api_association_accepts_its_own_slug(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)

    response = patch(client, association, association["slug"])

    assert response.status_code == 200
    assert response.json()["slug"] == association["slug"]


# /core/operations/update-association/volunteer
def test_patch_api_association_slug_403_for_a_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, _ = manager_and_volunteer(client, new_client)

    response = patch(bruno, association, unique_slug())

    assert response.status_code == 403
    assert "error" in response.json()
    assert slug_of(client, association) == association["slug"]


# /core/operations/update-association/malformed-slug
@pytest.mark.parametrize("slug", MALFORMED)
def test_patch_api_association_400_when_the_slug_is_malformed(client: Any, slug: str) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)

    response = patch(client, association, slug)

    assert response.status_code == 400
    assert "error" in response.json()
    assert slug_of(client, association) == association["slug"]


# /core/operations/update-association/malformed-slug /core/operations/general/refused
def test_patch_api_association_400_changes_no_name_when_the_slug_is_malformed(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)

    response = client.patch(
        f"/api/associations/{association['id']}",
        json={"name": "Jardin des Lilas", "slug": "Not A Slug"},
    )

    assert response.status_code == 400
    assert client.get(f"/api/associations/{association['id']}").json()["name"] == NAME


# /core/operations/update-association/taken
def test_patch_api_association_409_when_the_slug_is_taken_by_another(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)
    other = create_association(client, "Repair Café")

    response = patch(client, association, other["slug"])

    assert response.status_code == 409
    assert "error" in response.json()
    assert slug_of(client, association) == association["slug"]


# /core/operations/update-association/taken
def test_patch_api_association_409_when_the_slug_is_new(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)

    response = patch(client, association, "new")

    assert response.status_code == 409
    assert "error" in response.json()


# /core/operations/update-association/silent
def test_patch_api_association_slug_members_are_not_told(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, _, bruno_email = manager_and_volunteer(client, new_client)
    before = email_count(bruno_email)

    assert patch(client, association, unique_slug()).status_code == 200

    assert email_count(bruno_email) == before


# Former slugs


# /core/operations/update-association/new-slug
def test_the_former_slug_no_longer_leads_to_the_association(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)

    assert patch(client, association, unique_slug()).status_code == 200

    assert client.get(f"/api/associations/by-slug/{association['slug']}").status_code == 404


# /core/operations/update-association/new-slug
def test_another_association_can_take_the_former_slug(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, NAME)
    assert patch(client, association, unique_slug()).status_code == 200

    response = post(client, association["slug"])

    assert response.status_code == 201
    found = client.get(f"/api/associations/by-slug/{association['slug']}")
    assert found.json()["id"] == response.json()["id"]


# /core/operations/update-association/neither
def test_patch_api_association_400_when_neither_a_name_nor_a_slug_is_given(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, "Jardin partagé des Lilas")

    response = client.patch(f"/api/associations/{association['id']}", json={})

    assert response.status_code == 400
    after = client.get(f"/api/associations/{association['id']}").json()
    assert (after["name"], after["slug"]) == ("Jardin partagé des Lilas", association["slug"])
