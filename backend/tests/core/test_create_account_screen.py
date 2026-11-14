import re
import uuid
from collections.abc import Callable
from datetime import timedelta
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
    member_line,
    my_associations_listed,
    run_sql,
    shown,
    sign_in,
    sign_up,
    signed_in_as,
    unique_email,
    user_id_of,
)

EXISTS = "An account already exists for this email. Sign in instead."
NOT_INVITED = (
    "This email has not been invited. Ask a manager of your association to add you as a member."
)
NOT_SENT = "We couldn't send the confirmation email. Try again later."
GENERIC = "Something went wrong. Try again."
EMAIL_SENT = "Email sent."
LINK_INVALID = "This link is no longer valid."
NOT_JOINED = "not joined yet"

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
    # /core/ui/create-an-account/form
    def test_shows_the_form(self, client: Any) -> None:
        response = client.get("/signup")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert heading(response) == "Create an account"
        assert "Display name" in response.text
        assert "Email" in response.text
        assert 'type="password"' in response.text
        assert "Create account" in response.text

    # /core/ui/create-an-account/form
    def test_links_back_to_sign_in(self, client: Any) -> None:
        page = client.get("/signup").text

        assert "Already have an account?" in page
        assert re.search(r'<a[^>]*href="/"[^>]*>\s*Sign in\s*</a>', page)

    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert heading(client.get("/signup")) == "Créer un compte"

    # /core/ui/header/signed-out
    def test_has_the_signed_out_language_selector(self, client: Any) -> None:
        page = client.get("/signup").text

        assert "English" in page
        assert "Français" in page


class TestCreateAnAccountSuccess:
    # /core/ui/create-an-account/check-email
    # /core/operations/create-account/created
    # /core/ui/create-an-account/create
    def test_shows_the_message_and_stays_signed_out(self, client: Any) -> None:
        email = unique_email("Alice")

        response = create_account(client, "Alice", email)

        assert check_your_email(email) in shown(response)
        assert signed_in_as(client) is None
        assert heading(client.get("/")) == "Sign in"

    # /core/ui/create-an-account/check-email
    def test_offers_resend_the_email(self, client: Any) -> None:
        response = create_account(client, "Alice", unique_email("Alice"))

        assert "Resend the email" in shown(response)

    # /core/ui/create-an-account/check-email
    # /core/ui/header/language
    def test_the_message_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")
        email = unique_email("Alice")

        response = create_account(client, "Alice", email)

        assert email in shown(response)
        assert check_your_email(email) not in shown(response)

    def test_user_ids_are_uuids(self, client: Any) -> None:
        user = sign_up(client, "Alice")

        uuid.UUID(user["id"])

    # /core/operations/create-account/created
    # /core/operations/create-account/short-password
    def test_a_password_of_8_characters_is_accepted(self, client: Any) -> None:
        email = unique_email("Alice")

        response = create_account(client, "Alice", email, "12345678")

        assert check_your_email(email) in shown(response)


class TestConfirmationEmail:
    # /core/operations/create-account/confirmation
    def test_sends_a_confirmation_email(self, client: Any) -> None:
        email = unique_email("Alice")

        create_account(client, "Alice", email)

        latest_verification_token(email)  # raises if no email was sent

    # /core/model/emailverificationtoken/token
    def test_the_links_of_two_accounts_differ(self, client: Any) -> None:
        alice = unique_email("Alice")
        bruno = unique_email("Bruno")

        create_account(client, "Alice", alice)
        create_account(client, "Bruno", bruno)

        assert latest_verification_token(alice) != latest_verification_token(bruno)

    # /core/operations/create-account/confirmation
    def test_the_link_expires_24_hours_after_creation(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)

        expires_in = run_sql(
            "SELECT expires_at - now() FROM email_verification_token WHERE token = :token", token
        )

        assert timedelta(hours=23, minutes=59) < expires_in <= timedelta(hours=24)


class TestEmailLanguage:
    # /core/operations/create-account/language
    # /ui/language/default
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

    # /core/operations/create-account/language
    # /ui/language/default
    @pytest.mark.parametrize("accept_language", ["en", "en-GB,en;q=0.9,fr;q=0.8", "de", "*"])
    def test_in_english_otherwise(self, client: Any, accept_language: str) -> None:
        email = unique_email("Alice")

        create_account(client, "Alice", email, headers={"Accept-Language": accept_language})

        assert_written_in(latest_email(email), ENGLISH)

    # /core/operations/create-account/language
    # /ui/language/default
    def test_in_english_without_a_browser_preference(self, client: Any) -> None:
        email = unique_email("Alice")

        create_account(client, "Alice", email)

        assert_written_in(latest_email(email), ENGLISH)

    # /core/operations/create-account/language
    # /core/ui/header/language
    def test_the_language_cookie_wins_over_a_browser_that_prefers_english(
        self, client: Any
    ) -> None:
        client.cookies.set("language", "fr")
        email = unique_email("Alice")

        create_account(client, "Alice", email, headers={"Accept-Language": "en"})

        assert_written_in(latest_email(email), FRENCH)

    # /core/operations/create-account/language
    # /core/ui/header/language
    def test_the_language_cookie_wins_over_a_browser_that_prefers_french(self, client: Any) -> None:
        client.cookies.set("language", "en")
        email = unique_email("Alice")

        create_account(client, "Alice", email, headers={"Accept-Language": "fr"})

        assert_written_in(latest_email(email), ENGLISH)

    # /core/operations/resend-confirmation/resent
    # /core/operations/create-account/language
    # /core/ui/header/language
    def test_the_resent_email_follows_the_interface_at_that_moment(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        assert_written_in(latest_email(email), ENGLISH)
        client.cookies.set("language", "fr")

        resend(client, email)

        assert_written_in(latest_email(email), FRENCH)


class TestClaimAccount:
    # /core/operations/create-account/claimed
    # /core/ui/create-an-account/check-email
    def test_takes_over_a_user_without_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        member = add_member(client, association["slug"], "Chloé", chloe_email)
        chloe = new_client()

        response = create_account(chloe, "Chloé L.", chloe_email)

        assert check_your_email(chloe_email) in shown(response)
        confirm_email(chloe, latest_verification_token(chloe_email))
        assert "window.location" in shown(sign_in(chloe, chloe_email))
        assert user_id_of(chloe_email) == member["user_id"]
        assert signed_in_as(chloe) == "Chloé L."
        associations = my_associations_listed(chloe)
        assert [a.name for a in associations] == [association["name"]]
        assert "volunteer" in associations[0].text.lower()
        line = member_line(client, association["slug"], chloe_email)
        assert line.startswith(f"Chloé L. {chloe_email} ")


class TestExistingAccount:
    # /core/ui/create-an-account/exists
    # /core/operations/create-account/exists
    def test_shows_the_message(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        response = create_account(new_client(), "Other", email)

        assert EXISTS in shown(response)

    # /core/ui/create-an-account/exists
    # /core/operations/create-account/exists
    # /core/model/user/email
    def test_ignores_the_case_of_the_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        response = create_account(new_client(), "Other", email.upper())

        assert EXISTS in shown(response)

    # /core/operations/create-account/exists
    # /core/operations/general/refused
    def test_keeps_the_password(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        create_account(new_client(), "Other", email, "another password")

        browser = new_client()
        assert "window.location" in shown(sign_in(browser, email))
        assert signed_in_as(browser) == "Alice"


class TestInvitationOnly:
    # /core/ui/create-an-account/not-invited
    # /core/operations/create-account/not-invited
    # /core/operations/general/refused
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
        add_member(client, association["slug"], "Marie", email)
        line = member_line(client, association["slug"], email)
        assert line.startswith(f"Marie {NOT_JOINED} {email} ")

    # /core/operations/create-account/not-invited
    # /core/operations/create-account/claimed
    # /core/ui/create-an-account/check-email
    # /core/model/user/email
    def test_creates_the_account_of_an_added_member(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        add_member(client, association["slug"], "Chloé", chloe_email)
        monkeypatch.setenv("INVITATION_ONLY", "true")

        response = create_account(new_client(), "Chloé", chloe_email.upper())

        assert check_your_email(chloe_email.upper()) in shown(response)

    # /core/operations/create-account/created
    # /core/model/user
    # /core/ui/create-an-account/check-email
    def test_creates_the_account_of_the_superuser(
        self, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Root")
        monkeypatch.setenv("INVITATION_ONLY", "true")
        monkeypatch.setenv("SUPERUSER_EMAIL", email)

        response = create_account(new_client(), "Root", email)

        assert check_your_email(email) in shown(response)

    # /core/operations/create-account/created
    # /core/model/user
    def test_the_superusers_email_is_compared_ignoring_case(
        self, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Root")
        monkeypatch.setenv("INVITATION_ONLY", "true")
        monkeypatch.setenv("SUPERUSER_EMAIL", email.upper())

        response = create_account(new_client(), "Root", email)

        assert check_your_email(email) in shown(response)

    # /core/ui/create-an-account/not-invited
    # /core/operations/create-account/not-invited
    # /core/model/user
    def test_another_email_than_the_superusers_shows_the_message(
        self, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Mallory")
        monkeypatch.setenv("INVITATION_ONLY", "true")
        monkeypatch.setenv("SUPERUSER_EMAIL", unique_email("Root"))

        response = create_account(new_client(), "Mallory", email)

        assert NOT_INVITED in shown(response)

    # /core/ui/create-an-account/not-invited
    # /core/operations/create-account/not-invited
    # /core/model/user
    def test_with_no_superuser_shows_the_message(
        self, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Mallory")
        monkeypatch.setenv("INVITATION_ONLY", "true")
        monkeypatch.delenv("SUPERUSER_EMAIL", raising=False)

        response = create_account(new_client(), "Mallory", email)

        assert NOT_INVITED in shown(response)

    # /core/ui/create-an-account/exists
    # /core/operations/create-account/exists
    def test_an_email_with_an_account_still_shows_that_message(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        monkeypatch.setenv("INVITATION_ONLY", "true")

        response = create_account(new_client(), "Alice", email)

        assert EXISTS in shown(response)

    # /core/operations/create-account/created
    # /core/ui/create-an-account/check-email
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


class TestEmailNotSent:
    # /core/ui/create-an-account/not-sent
    # /core/operations/create-account/not-sent
    # /core/operations/general/refused
    def test_shows_the_message_and_saves_nothing(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Alice")
        break_the_mailer(monkeypatch)

        response = create_account(client, "Alice", email)

        assert NOT_SENT in shown(response)
        monkeypatch.undo()
        assert check_your_email(email) in shown(create_account(client, "Alice", email))

    # /core/ui/create-an-account/not-sent
    # /core/operations/create-account/not-sent
    # /core/operations/general/refused
    def test_leaves_a_user_without_password_unchanged(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        add_member(client, association["slug"], "Chloé", chloe_email)
        chloe = new_client()
        break_the_mailer(monkeypatch)

        response = create_account(chloe, "Chloé L.", chloe_email)

        assert NOT_SENT in shown(response)
        line = member_line(client, association["slug"], chloe_email)
        assert line.startswith(f"Chloé {NOT_JOINED} {chloe_email} ")


class TestCaseOrder:
    # /core/operations/create-account/short-password
    # /core/operations/create-account/exists
    # /ui/errors/generic
    def test_a_short_password_on_an_existing_email_is_refused_as_short(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        text = shown(create_account(new_client(), "Other", email, "1234567"))

        assert GENERIC in text
        assert EXISTS not in text


class TestInitialState:
    # /core/operations/initial-state/empty
    def test_an_email_never_used_has_no_user(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")

        assert "window.location" not in shown(sign_in(client, email))
        assert check_your_email(email) in shown(create_account(new_client(), "Alice", email))


class TestInvalidFields:
    # /core/operations/create-account/short-password
    # /ui/errors/generic
    # /core/operations/general/refused
    def test_a_short_password_shows_the_generic_error_message_and_saves_nothing(
        self, client: Any
    ) -> None:
        email = unique_email("Alice")

        response = create_account(client, "Alice", email, "1234567")

        assert GENERIC in shown(response)
        assert email_count(email) == 0
        assert check_your_email(email) in shown(create_account(client, "Alice", email))

    # /core/operations/general/malformed
    # /core/model/user/display-name
    # /ui/errors/generic
    # /core/operations/general/refused
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

    # /ui/errors/generic
    def test_a_body_that_is_not_json_shows_the_generic_error_message(self, client: Any) -> None:
        response = client.post(
            "/signup", content=b"{not json", headers={"content-type": "application/json"}
        )

        assert GENERIC in shown(response)


class TestResendTheEmail:
    # /core/ui/create-an-account/resend
    # /core/operations/resend-confirmation/resent
    def test_shows_email_sent_and_sends_a_new_email(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        latest_verification_token(email)

        response = resend(client, email)

        assert EMAIL_SENT in shown(response)
        assert email_count(email) == 2

    # /core/model/emailverificationtoken/single
    # /core/operations/create-account/confirmation
    # /core/operations/confirm-email/invalid
    # /core/operations/resend-confirmation/resent
    # /core/operations/confirm-email/confirmed
    def test_invalidates_the_previous_token(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        first_token = latest_verification_token(email)

        resend(client, email)

        assert LINK_INVALID in shown(confirm_email(client, first_token))
        second_token = latest_verification_token(email)
        assert LINK_INVALID not in shown(confirm_email(client, second_token))
        assert heading(client.get("/")) == "My associations"

    # /core/ui/create-an-account/resend
    # /core/operations/resend-confirmation/ignored
    # /core/operations/resend-confirmation/answer
    def test_shows_the_same_for_an_unknown_email(self, client: Any) -> None:
        email = unique_email("Nobody")

        response = resend(client, email)

        assert EMAIL_SENT in shown(response)
        assert email_count(email) == 0

    # /core/ui/create-an-account/resend
    # /core/operations/resend-confirmation/ignored
    # /core/operations/resend-confirmation/answer
    def test_shows_the_same_and_sends_nothing_when_already_confirmed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        before = email_count(email)

        response = resend(new_client(), email)

        assert EMAIL_SENT in shown(response)
        assert email_count(email) == before

    # /core/ui/create-an-account/resend
    # /core/operations/resend-confirmation/answer
    def test_shows_the_same_when_the_email_cannot_be_sent(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        break_the_mailer(monkeypatch)

        response = resend(client, email)

        assert EMAIL_SENT in shown(response)

    # /core/ui/create-an-account/resend
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        response = resend(client, unique_email("Nobody"))

        assert EMAIL_SENT not in shown(response)


class TestConfirmEmail:
    def test_the_link_answers_a_page(self, client: Any) -> None:
        response = client.get("/verify-email?token=anything")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

    # /core/ui/confirm-email/confirmed
    # /core/operations/confirm-email/confirmed
    def test_success_signs_in_and_leads_to_my_associations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)

        response = confirm_email(client, latest_verification_token(email))

        assert LINK_INVALID not in shown(response)
        assert signed_in_as(client) == "Alice"
        assert heading(client.get("/")) == "My associations"
        assert "window.location" in shown(sign_in(new_client(), email))

    # /core/operations/sign-in/new-session
    def test_replaces_a_session_id_planted_in_the_browser(
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
        assert signed_in_as(attacker) is None

    # /core/ui/confirm-email/fetched
    def test_fetching_the_link_leaves_the_token_usable(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)

        client.get(f"/verify-email?token={token}")

        assert signed_in_as(client) is None
        assert LINK_INVALID not in shown(confirm_email(client, token))
        assert signed_in_as(client) is not None

    # /core/ui/confirm-email/status
    def test_the_page_answers_200_whether_the_link_is_valid_or_not(self, client: Any) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)

        assert client.get(f"/verify-email?token={token}").status_code == 200
        assert client.get("/verify-email?token=unknown-token").status_code == 200
        assert client.get("/verify-email").status_code == 200

    def test_the_page_carries_the_token_to_its_action_safely(self, client: Any) -> None:
        response = client.get("/verify-email", params={"token": '"><script>alert(1)</script>'})

        assert response.status_code == 200
        assert "<script>alert(1)</script>" not in response.text


class TestConfirmEmailInvalidLink:
    def assert_shows_the_message(self, response: Any) -> None:
        text = shown(response)
        assert LINK_INVALID in text
        assert re.search(r'<a[^>]*href="/signup"', text)

    # /core/ui/confirm-email/invalid
    # /core/operations/confirm-email/invalid
    def test_unknown_token(self, client: Any) -> None:
        self.assert_shows_the_message(confirm_email(client, "unknown-token"))
        assert signed_in_as(client) is None

    # /core/ui/confirm-email/invalid
    # /core/ui/confirm-email/no-token
    def test_no_token(self, client: Any) -> None:
        self.assert_shows_the_message(client.post("/verify-email", json={}))

    # /core/ui/confirm-email/invalid
    # /core/operations/confirm-email/invalid
    def test_already_used_token(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        create_account(client, "Alice", email)
        token = latest_verification_token(email)
        confirm_email(client, token)

        self.assert_shows_the_message(confirm_email(new_client(), token))

    # /core/ui/confirm-email/invalid
    # /core/operations/confirm-email/invalid
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
        assert signed_in_as(client) is None

    # /core/ui/confirm-email/invalid
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        text = shown(confirm_email(client, "unknown-token"))

        assert "Ce lien n'est plus valide." in text
