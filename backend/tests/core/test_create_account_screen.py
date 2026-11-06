import re
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    PASSWORD,
    add_member,
    break_the_mailer,
    confirm_email,
    create_account,
    create_association,
    email_count,
    heading,
    latest_email,
    latest_verification_token,
    run_sql,
    shown,
    sign_up,
    unique_email,
)

EXISTS = "An account already exists for this email. Sign in instead."
NOT_INVITED = (
    "This email has not been invited. Ask a manager of your association to add you as a member."
)
NOT_SENT = "We couldn't send the confirmation email. Try again later."
GENERIC = "Something went wrong. Try again."
EMAIL_SENT = "Email sent."
LINK_INVALID = "This link is no longer valid."

ENGLISH = {"Subject": "Confirm your email", "Text": "Confirm your email by opening this link:"}
FRENCH = {
    "Subject": "Confirmez votre adresse e-mail",
    "Text": "Confirmez votre adresse e-mail en ouvrant ce lien :",
}


def check_your_email(email: str) -> str:
    return f"Check {email} for a confirmation link."


def resend(client: Any, email: str, **kwargs: Any) -> Any:
    return client.post("/signup/resend", json={"email": email}, **kwargs)


def assert_written_in(sent: dict[str, str], language: dict[str, str]) -> None:
    assert sent["Subject"] == language["Subject"]
    assert sent["Text"].startswith(language["Text"])
    assert re.search(r"/verify-email\?token=[\w-]+", sent["Text"])


class TestCreateAnAccountForm:
    def test_shows_the_form(self, client: Any) -> None:
        response = client.get("/signup")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert heading(response) == "Create an account"
        assert "Display name" in response.text
        assert "Email" in response.text
        assert 'type="password"' in response.text
        assert "Create account" in response.text

    def test_links_back_to_sign_in(self, client: Any) -> None:
        page = client.get("/signup").text

        assert "Already have an account?" in page
        assert re.search(r'<a[^>]*href="/"[^>]*>\s*Sign in\s*</a>', page)

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert heading(client.get("/signup")) == "Créer un compte"

    def test_has_the_signed_out_language_selector(self, client: Any) -> None:
        page = client.get("/signup").text

        assert "English" in page
        assert "Français" in page


class TestCreateAnAccountSuccess:
    def test_shows_the_message_and_stays_signed_out(self, client: Any) -> None:
        email = unique_email("Alice")

        response = create_account(client, "Alice", email)

        assert check_your_email(email) in shown(response)
        assert client.get("/api/session").status_code == 401
        assert heading(client.get("/")) == "Sign in"

    def test_offers_resend_the_email(self, client: Any) -> None:
        response = create_account(client, "Alice", unique_email("Alice"))

        assert "Resend the email" in shown(response)

    def test_the_message_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")
        email = unique_email("Alice")

        response = create_account(client, "Alice", email)

        assert email in shown(response)
        assert check_your_email(email) not in shown(response)

    def test_user_ids_are_uuids(self, client: Any) -> None:
        user = sign_up(client, "Alice")

        uuid.UUID(user["id"])

    def test_a_password_of_8_characters_is_accepted(self, client: Any) -> None:
        email = unique_email("Alice")

        response = create_account(client, "Alice", email, "12345678")

        assert check_your_email(email) in shown(response)


class TestR9:
    def test_sends_a_confirmation_email(self, client: Any) -> None:
        email = unique_email("Alice")

        create_account(client, "Alice", email)

        latest_verification_token(email)  # raises if no email was sent


class TestR20:
    @pytest.mark.parametrize(
        "accept_language",
        ["fr", "fr-FR", "fr-FR,fr;q=0.9,en;q=0.8", "de,fr;q=0.5", "en;q=0.4,fr;q=0.9"],
    )
    def test_in_french_when_the_browser_prefers_french(
        self, client: Any, accept_language: str
    ) -> None:
        email = unique_email("Alice")

        create_account(client, "Alice", email, headers={"Accept-Language": accept_language})

        assert_written_in(latest_email(email), FRENCH)

    @pytest.mark.parametrize("accept_language", ["en", "en-GB,en;q=0.9,fr;q=0.8", "de", "*"])
    def test_in_english_otherwise(self, client: Any, accept_language: str) -> None:
        email = unique_email("Alice")

        create_account(client, "Alice", email, headers={"Accept-Language": accept_language})

        assert_written_in(latest_email(email), ENGLISH)

    def test_in_english_without_a_browser_preference(self, client: Any) -> None:
        email = unique_email("Alice")

        create_account(client, "Alice", email)

        assert_written_in(latest_email(email), ENGLISH)

    def test_the_language_cookie_wins_over_a_browser_that_prefers_english(
        self, client: Any
    ) -> None:
        client.cookies.set("language", "fr")
        email = unique_email("Alice")

        create_account(client, "Alice", email, headers={"Accept-Language": "en"})

        assert_written_in(latest_email(email), FRENCH)

    def test_the_language_cookie_wins_over_a_browser_that_prefers_french(self, client: Any) -> None:
        client.cookies.set("language", "en")
        email = unique_email("Alice")

        create_account(client, "Alice", email, headers={"Accept-Language": "fr"})

        assert_written_in(latest_email(email), ENGLISH)

    def test_the_resent_email_follows_the_interface_at_that_moment(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        assert_written_in(latest_email(email), ENGLISH)
        client.cookies.set("language", "fr")

        resend(client, email)

        assert_written_in(latest_email(email), FRENCH)


class TestR2:
    def test_takes_over_a_user_without_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        member = add_member(client, association["id"], "Chloé", chloe_email).json()
        chloe = new_client()

        response = create_account(chloe, "Chloé L.", chloe_email)

        assert check_your_email(chloe_email) in shown(response)
        confirm_email(chloe, latest_verification_token(chloe_email))
        signed_in = chloe.post("/api/session", json={"email": chloe_email, "password": PASSWORD})
        assert signed_in.status_code == 200
        assert signed_in.json()["id"] == member["user_id"]
        assert signed_in.json()["display_name"] == "Chloé L."
        associations = chloe.get("/api/associations").json()
        assert [(a["id"], a["role"]) for a in associations] == [(association["id"], "volunteer")]
        members = client.get(f"/api/associations/{association['id']}").json()["members"]
        chloe_member = next(m for m in members if m["user_id"] == member["user_id"])
        assert chloe_member["has_account"] is True
        assert chloe_member["email_verified"] is True
        assert chloe_member["display_name"] == "Chloé L."


class TestExistingAccount:
    def test_shows_the_message(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        response = create_account(new_client(), "Other", email)

        assert EXISTS in shown(response)

    def test_ignores_the_case_of_the_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        response = create_account(new_client(), "Other", email.upper())

        assert EXISTS in shown(response)

    def test_keeps_the_password(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        create_account(new_client(), "Other", email, "another password")

        signed_in = new_client().post("/api/session", json={"email": email, "password": PASSWORD})
        assert signed_in.status_code == 200
        assert signed_in.json()["display_name"] == "Alice"


class TestR19:
    def test_shows_the_message_for_an_email_not_invited_and_saves_nothing(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        email = unique_email("Mallory")
        monkeypatch.setenv("INVITATION_ONLY", "true")

        response = create_account(new_client(), "Mallory", email)

        assert NOT_INVITED in shown(response)
        # Nothing saved: adding the email afterwards creates a new user, named by the manager.
        member = add_member(client, association["id"], "Marie", email).json()
        assert member["display_name"] == "Marie"
        assert member["has_account"] is False

    def test_creates_the_account_of_an_added_member(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        add_member(client, association["id"], "Chloé", chloe_email)
        monkeypatch.setenv("INVITATION_ONLY", "true")

        response = create_account(new_client(), "Chloé", chloe_email.upper())

        assert check_your_email(chloe_email.upper()) in shown(response)

    def test_creates_the_account_of_the_superuser(
        self, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Root")
        monkeypatch.setenv("INVITATION_ONLY", "true")
        monkeypatch.setenv("SUPERUSER_EMAIL", email)

        response = create_account(new_client(), "Root", email)

        assert check_your_email(email) in shown(response)

    def test_an_email_with_an_account_still_shows_that_message(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        monkeypatch.setenv("INVITATION_ONLY", "true")

        response = create_account(new_client(), "Alice", email)

        assert EXISTS in shown(response)

    @pytest.mark.parametrize("value", [None, "", "false", "yes"])
    def test_sign_up_is_open_unless_invitation_only_is_true(
        self, value: str | None, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if value is None:
            monkeypatch.delenv("INVITATION_ONLY", raising=False)
        else:
            monkeypatch.setenv("INVITATION_ONLY", value)
        email = unique_email("Alice")

        response = create_account(new_client(), "Alice", email)

        assert check_your_email(email) in shown(response)


class TestR10:
    def test_shows_the_message_and_saves_nothing(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Alice")
        break_the_mailer(monkeypatch)

        response = create_account(client, "Alice", email)

        assert NOT_SENT in shown(response)
        monkeypatch.undo()
        assert check_your_email(email) in shown(create_account(client, "Alice", email))

    def test_leaves_a_user_without_password_unchanged(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        member = add_member(client, association["id"], "Chloé", chloe_email).json()
        chloe = new_client()
        break_the_mailer(monkeypatch)

        response = create_account(chloe, "Chloé L.", chloe_email)

        assert NOT_SENT in shown(response)
        members = client.get(f"/api/associations/{association['id']}").json()["members"]
        chloe_member = next(m for m in members if m["user_id"] == member["user_id"])
        assert chloe_member["has_account"] is False
        assert chloe_member["display_name"] == "Chloé"


class TestInvalidFields:
    def test_a_short_password_shows_the_generic_error_message_and_saves_nothing(
        self, client: Any
    ) -> None:
        email = unique_email("Alice")

        response = create_account(client, "Alice", email, "1234567")

        assert GENERIC in shown(response)
        assert email_count(email) == 0
        assert check_your_email(email) in shown(create_account(client, "Alice", email))

    @pytest.mark.parametrize(
        "signals",
        [
            {"email": "missing-name@example.org", "password": PASSWORD},
            {"displayName": "", "email": "empty-name@example.org", "password": PASSWORD},
            {"displayName": "Alice", "password": PASSWORD},
            {"displayName": "Alice", "email": "not-an-email", "password": PASSWORD},
            {"displayName": "Alice", "email": "missing-password@example.org"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_message(
        self, client: Any, signals: dict[str, str]
    ) -> None:
        response = client.post("/signup", json=signals)

        assert GENERIC in shown(response)
        if "@" in signals.get("email", ""):
            assert email_count(signals["email"]) == 0

    def test_a_body_that_is_not_json_shows_the_generic_error_message(self, client: Any) -> None:
        response = client.post(
            "/signup", content=b"{not json", headers={"content-type": "application/json"}
        )

        assert GENERIC in shown(response)


class TestResendTheEmail:
    def test_shows_email_sent_and_sends_a_new_email(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        latest_verification_token(email)

        response = resend(client, email)

        assert EMAIL_SENT in shown(response)
        assert email_count(email) == 2

    def test_r8_invalidates_the_previous_token(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        first_token = latest_verification_token(email)

        resend(client, email)

        assert LINK_INVALID in shown(confirm_email(client, first_token))
        second_token = latest_verification_token(email)
        assert LINK_INVALID not in shown(confirm_email(client, second_token))
        assert heading(client.get("/")) == "My associations"

    def test_shows_the_same_for_an_unknown_email(self, client: Any) -> None:
        email = unique_email("Nobody")

        response = resend(client, email)

        assert EMAIL_SENT in shown(response)
        assert email_count(email) == 0

    def test_shows_the_same_and_sends_nothing_when_already_confirmed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        before = email_count(email)

        response = resend(new_client(), email)

        assert EMAIL_SENT in shown(response)
        assert email_count(email) == before

    def test_shows_the_same_when_the_email_cannot_be_sent(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        break_the_mailer(monkeypatch)

        response = resend(client, email)

        assert EMAIL_SENT in shown(response)

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        response = resend(client, unique_email("Nobody"))

        assert EMAIL_SENT not in shown(response)


class TestConfirmEmail:
    def test_the_link_answers_a_page(self, client: Any) -> None:
        response = client.get("/verify-email?token=anything")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

    def test_success_signs_in_and_leads_to_my_associations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)

        response = confirm_email(client, latest_verification_token(email))

        assert LINK_INVALID not in shown(response)
        assert client.get("/api/session").json()["email"] == email
        assert heading(client.get("/")) == "My associations"
        signed_in = new_client().post("/api/session", json={"email": email, "password": PASSWORD})
        assert signed_in.status_code == 200

    def test_r16_replaces_a_session_id_planted_in_the_browser(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)
        planted = uuid.uuid4().hex
        client.cookies.set("session", planted)
        attacker = new_client()
        attacker.cookies.set("session", planted)

        response = confirm_email(client, token)

        assert response.cookies.get("session") not in (None, planted)
        assert attacker.get("/api/session").status_code == 401

    def test_fetching_the_link_leaves_the_token_usable(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)

        client.get(f"/verify-email?token={token}")

        assert client.get("/api/session").status_code == 401
        assert LINK_INVALID not in shown(confirm_email(client, token))
        assert client.get("/api/session").status_code == 200

    def test_the_page_carries_the_token_to_its_action_safely(self, client: Any) -> None:
        response = client.get("/verify-email", params={"token": '"><script>alert(1)</script>'})

        assert response.status_code == 200
        assert "<script>alert(1)</script>" not in response.text


class TestConfirmEmailInvalidLink:
    def assert_shows_the_message(self, response: Any) -> None:
        text = shown(response)
        assert LINK_INVALID in text
        assert re.search(r'<a[^>]*href="/signup"', text)

    def test_unknown_token(self, client: Any) -> None:
        self.assert_shows_the_message(confirm_email(client, "unknown-token"))
        assert client.get("/api/session").status_code == 401

    def test_no_token(self, client: Any) -> None:
        self.assert_shows_the_message(client.post("/verify-email", json={}))

    def test_already_used_token(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)
        confirm_email(client, token)

        self.assert_shows_the_message(confirm_email(new_client(), token))

    def test_expired_token(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)
        run_sql(
            "UPDATE email_verification_token SET expires_at = now() - interval '1 second'"
            " WHERE token = :token",
            token,
        )

        self.assert_shows_the_message(confirm_email(client, token))
        assert client.get("/api/session").status_code == 401

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        text = shown(confirm_email(client, "unknown-token"))

        assert "Ce lien n'est plus valide." in text


class TestEndpointsRemoved:
    @pytest.mark.parametrize(
        "path", ["/api/accounts", "/api/accounts/verify", "/api/accounts/verify/resend"]
    )
    def test_answers_404(self, client: Any, path: str) -> None:
        assert client.post(path, json={}).status_code == 404
