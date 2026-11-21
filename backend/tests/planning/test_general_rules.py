"""The statements of `## General` of the operations, each checked by one test over a table of the
actions of the screens. The table is compared with the routes of the application, so that a new
action cannot miss its row."""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import pytest
from litestar.testing import TestClient

from gilda.app import create_app
from tests.core.conftest import (
    ask_for_reset,
    create_account,
    email_count,
    latest_access_token,
    latest_reset_token,
    latest_verification_token,
    send_member_link,
    signed_in_as,
    unique_slug,
)
from tests.core.test_session_in_flight import hold, stored
from tests.page import dialog_opened_by, parse, text_of
from tests.planning.conftest import (
    GENERIC,
    add_absence_of,
    add_closure,
    add_member,
    add_slot,
    added_id,
    create_association,
    create_share_link,
    day_of_week,
    opened_weeks,
    patched,
    propose,
    save_note,
    set_period,
    share_link_shown,
    shown,
    sign_up,
    unique_email,
)

SIGNED_OUT = "window.location = '/'"


class World:
    """Alice and Bruno manage an association, each signed in on their own client; Chloé
    volunteers there, without an account. It has a
    Thursday slot, a closure, a planning period, an absence and a note of Alice's, a registration
    of Alice's, one proposed to her by Bruno, and a share link; Bruno has an access link. Zoé has
    created her account without confirming it, and Alice has asked for a password reset."""

    def __init__(self, client: Any, new_client: Callable[[], Any]) -> None:
        self.new_client = new_client
        self.alice = client
        alice = sign_up(client, "Alice")
        self.alice_email, self.alice_id = alice["email"], alice["id"]
        association = create_association(client)
        self.slug = association["slug"]
        self.bruno = new_client()
        self.bruno_email = unique_email("Bruno")
        self.bruno_id = sign_up(self.bruno, "Bruno", self.bruno_email)["id"]
        add_member(client, self.slug, "Bruno", self.bruno_email, "manager")
        self.chloe_email = unique_email("Chloe")
        self.chloe_id = add_member(client, self.slug, "Chloé", self.chloe_email)["user_id"]
        self.slot = add_slot(client, association, "thursday", "10:00", "13:00")
        self.closure = add_closure(
            client, association, day_of_week("saturday", 6), day_of_week("sunday", 6)
        )
        period = (day_of_week("monday", 0), day_of_week("sunday", 5))
        assert GENERIC not in shown(set_period(client, self.slug, *period))
        self.absence = add_absence_of(
            client, association, day_of_week("monday", 5), day_of_week("tuesday", 5)
        )
        assert GENERIC not in shown(save_note(client, self.slug, "Mornings"))
        self.own = self._registered(client, association, day_of_week("thursday", 1))
        self.proposed = self._registered(self.bruno, association, day_of_week("thursday", 2))
        assert GENERIC not in shown(create_share_link(client, self.slug))
        token = share_link_shown(client, self.slug)
        assert token
        self.share_token = token
        assert GENERIC not in text_of(
            patched(send_member_link(self.alice, self.slug, self.bruno_id))
        )

    def _registered(self, as_client: Any, association: dict[str, Any], day: str) -> dict[str, Any]:
        """Registers Alice on the Thursday of `day` by her name in its menu, signed in on
        `as_client`."""

        def register() -> None:
            response = propose(
                as_client, self.slug, self.alice_id, day, "10:00", "13:00", {"from": day, "to": day}
            )
            assert GENERIC not in shown(response)

        return {"id": added_id("registration", association["id"], register)}

    @cached_property
    def access_token(self) -> str:
        return latest_access_token(self.bruno_email)

    @cached_property
    def last(self) -> dict[str, Any]:
        """The snapshot as last taken."""
        return self.snapshot()

    @cached_property
    def zoe_email(self) -> str:
        """The email of Zoé, who has created her account without confirming it: no screen of
        the snapshot shows her."""
        email = unique_email("Zoe")
        assert create_account(self.new_client(), "Zoé", email).status_code == 200
        return email

    @cached_property
    def verification_token(self) -> str:
        return latest_verification_token(self.zoe_email)

    @cached_property
    def reset_token(self) -> str:
        """The token of the password reset Alice asks for, which no screen shows."""
        assert ask_for_reset(self.new_client(), self.alice_email).status_code == 200
        return latest_reset_token(self.alice_email)

    def snapshot(self) -> dict[str, Any]:
        """The state as the screens show it: the pages of the association to Alice, as their HTML
        holds them, closed dialogs and selected options included, the share link among them; who is
        signed in on Bruno's client; how many emails Chloé was sent."""
        slug = self.slug
        pages = {
            "alice /": (self.alice, "/"),
            "alice schedule": (self.alice, f"/association/{slug}"),
            "alice members": (self.alice, f"/association/{slug}/members"),
            "alice settings": (self.alice, f"/association/{slug}/settings"),
            "alice availability": (self.alice, f"/association/{slug}/availability"),
        }
        state: dict[str, Any] = {}
        for name, (as_client, path) in pages.items():
            response = as_client.get(path)
            assert response.status_code == 200, path
            state[name] = _main(response.text)
        state["bruno signed in"] = signed_in_as(self.bruno)
        state["emails to Chloé"] = email_count(self.chloe_email)
        return state

    def unchanged(self) -> bool:
        """Whether the snapshot is the same as when last taken; takes it again."""
        now = self.snapshot()
        same = now == self.last
        self.last = now
        return same


def _main(page: str) -> str:
    """The HTML of the page's main, with every element, shown or not, and of the dialogs that
    its edit icons open."""
    root = parse(page)
    main = next(root.elements("main", hidden=True))
    dialogs = [
        dialog_opened_by(page, button).html
        for button in root.elements("button", hidden=True)
        if button.get("command") == "show-modal"
        and (button.get("aria-label") or "").startswith("Edit ")
    ]
    return "\n".join([_all_html(main), *dialogs])


def _all_html(element: Any) -> str:
    attributes = "".join(
        f" {name}" if value is None else f' {name}="{value}"'
        for name, value in element.attrs.items()
    )
    inner = "".join(
        child if isinstance(child, str) else _all_html(child) for child in element.children
    )
    return f"<{element.tag}{attributes}>{inner}</{element.tag}>"


@dataclass(frozen=True)
class Action:
    """An action of the screens: its route, as the application declares it, the signals its
    screen sends, and which inputs of its operation it takes."""

    route: str
    signals: Callable[[World], dict[str, Any]] = lambda _: {}
    params: Callable[[World], dict[str, str]] = lambda _: {}
    method: str = "POST"
    user: bool = True
    """Its operation has an input `user`."""
    association: bool = True
    """Its operation has an input `association`, from the slug of the route."""
    wrong: dict[str, list[Any]] = field(default_factory=dict)
    """Each signal that is an input of its operation, or of its trigger, with values not of its
    type; each is also left out."""
    ids: tuple[str, ...] = ()
    """The route's parameters, besides the slug, that are inputs of its operation."""
    by_bruno: bool = False
    """Run by Bruno rather than Alice, when signed in."""
    kept_nothing: Callable[[World, dict[str, Any]], None] | None = None
    """Checks, once the action was refused with these signals, what the snapshot does not
    show."""

    def path(self, world: World, slug: str | None = None, **changed: str) -> str:
        values = {"slug": world.slug if slug is None else slug, **self.params(world), **changed}
        path = self.route
        for name, value in values.items():
            for kind in ("str", "uuid"):
                path = path.replace(f"{{{name}:{kind}}}", value)
        return path

    def run(
        self,
        as_client: Any,
        world: World,
        signals: dict[str, Any] | None = None,
        slug: str | None = None,
        **changed: str,
    ) -> Any:
        path = self.path(world, slug, **changed)
        sent = self.signals(world) if signals is None else signals
        if self.method == "GET":
            return as_client.get(path, params=sent)
        return as_client.post(path, json=sent)


DATE = ["not a date"]
TIME = ["25:00"]
TEXT = [12]
EMAIL = ["not an email", 12]
NAME = ["", 12]
ROLE = ["owner"]
VALUE = ["sometimes"]
WEEKDAY = ["someday"]


def _account_can_be_created(w: World, signals: dict[str, Any]) -> None:
    """The email of a refused Create account can still create an account."""
    email = signals.get("email")
    if isinstance(email, str) and "@" in email:
        response = create_account(w.new_client(), "Yann", email)
        assert f"Check {email} for a confirmation link." in text_of(patched(response))


def _slug_is_free(w: World, signals: dict[str, Any]) -> None:
    """The slug of a refused Create association can still be taken, by Bruno."""
    slug = signals.get("slug")
    if isinstance(slug, str):
        response = w.bruno.post("/association/new", json={"name": "Les Lilas", "slug": slug})
        assert f"/association/{slug}" in shown(response)


def _menu_signals(w: World) -> dict[str, Any]:
    return {"date": day_of_week("thursday", 1), "start": "10:00", "end": "13:00", **opened_weeks()}


def _register_signals(weeks_ahead: int) -> Callable[[World], dict[str, Any]]:
    def signals(w: World) -> dict[str, Any]:
        day = day_of_week("thursday", weeks_ahead)
        return {"date": day, "start": "10:00", "end": "13:00", **opened_weeks()}

    return signals


A = "/association/{slug:str}"

ACTIONS: dict[str, Action] = {
    # Account and session
    "sign in": Action(
        "/sign-in",
        lambda w: {"email": w.alice_email, "password": "correct horse"},
        user=False,
        association=False,
        wrong={"email": EMAIL, "password": TEXT},
    ),
    "sign out": Action("/sign-out", user=False, association=False),
    "delete account": Action("/delete-account", association=False),
    "revoke my access link": Action("/revoke-access-link", association=False, by_bruno=True),
    "create account": Action(
        "/signup",
        lambda w: {"displayName": "Yann", "email": unique_email("Yann"), "password": "long enough"},
        user=False,
        association=False,
        wrong={"displayName": NAME, "email": EMAIL, "password": TEXT},
        kept_nothing=lambda w, signals: _account_can_be_created(w, signals),
    ),
    "resend confirmation": Action(
        "/signup/resend",
        lambda w: {"email": w.zoe_email},
        user=False,
        association=False,
        wrong={"email": EMAIL},
    ),
    "confirm email": Action(
        "/verify-email",
        lambda w: {"token": w.verification_token},
        user=False,
        association=False,
        wrong={"token": TEXT},
    ),
    "request password reset": Action(
        "/forgot-password",
        lambda w: {"email": w.alice_email},
        user=False,
        association=False,
        wrong={"email": EMAIL},
    ),
    "reset password": Action(
        "/reset-password",
        lambda w: {"token": w.reset_token, "password": "another long one"},
        user=False,
        association=False,
        wrong={"token": TEXT, "password": TEXT},
    ),
    "request access link": Action(
        "/sign-in-link",
        lambda w: {"email": w.bruno_email},
        user=False,
        association=False,
        wrong={"email": EMAIL},
    ),
    "sign in by access link": Action(
        "/access",
        lambda w: {"token": w.access_token},
        user=False,
        association=False,
        wrong={"token": TEXT},
    ),
    "language": Action("/language", lambda w: {"language": "fr"}, user=False, association=False),
    "notice": Action("/notice", method="GET", user=False, association=False),
    # Associations and members
    "create association": Action(
        "/association/new",
        lambda w: {"name": "Les Lilas", "slug": unique_slug()},
        association=False,
        wrong={"name": NAME, "slug": TEXT},
        kept_nothing=lambda w, signals: _slug_is_free(w, signals),
    ),
    "add member": Action(
        A + "/members",
        lambda w: {"displayName": "Yann", "email": unique_email("Yann"), "role": "volunteer"},
        wrong={"displayName": NAME, "email": EMAIL, "role": ROLE},
    ),
    "change role": Action(
        A + "/members/{user_id:uuid}/role",
        lambda w: {"role": "manager"},
        lambda w: {"user_id": w.chloe_id},
        wrong={"role": ROLE},
        ids=("user_id",),
    ),
    "remove member": Action(
        A + "/members/{user_id:uuid}/remove",
        params=lambda w: {"user_id": w.chloe_id},
        ids=("user_id",),
    ),
    "send access link": Action(
        A + "/members/{user_id:uuid}/send-link",
        params=lambda w: {"user_id": w.chloe_id},
        ids=("user_id",),
    ),
    "revoke access link": Action(
        A + "/members/{user_id:uuid}/revoke-link",
        params=lambda w: {"user_id": w.bruno_id},
        ids=("user_id",),
    ),
    "rename association": Action(
        A + "/rename", lambda w: {"name": "Les Lilas"}, wrong={"name": NAME}
    ),
    "change identifier": Action(
        A + "/identifier", lambda w: {"slug": unique_slug()}, wrong={"slug": TEXT}
    ),
    "delete association": Action(A + "/delete"),
    # Schedule settings
    "add slot": Action(
        A + "/settings/slots",
        lambda w: {"weekday": "saturday", "start": "10:00", "end": "13:00"},
        wrong={"weekday": WEEKDAY, "start": TIME, "end": TIME},
    ),
    "edit slot": Action(
        A + "/settings/slots/{slot_id:str}/edit",
        lambda w: {"weekday": "friday", "start": "10:00", "end": "13:00"},
        lambda w: {"slot_id": w.slot["id"]},
        wrong={"weekday": WEEKDAY, "start": TIME, "end": TIME},
        ids=("slot_id",),
    ),
    "delete slot": Action(
        A + "/settings/slots/{slot_id:str}/delete",
        params=lambda w: {"slot_id": w.slot["id"]},
        ids=("slot_id",),
    ),
    "set planning period": Action(
        A + "/settings/period",
        lambda w: {"first": day_of_week("monday", 1), "last": day_of_week("sunday", 8)},
        wrong={"first": DATE, "last": DATE},
    ),
    "clear planning period": Action(A + "/settings/period/clear"),
    "add closure": Action(
        A + "/settings/closures",
        lambda w: {
            "first": day_of_week("monday", 7),
            "last": day_of_week("friday", 7),
            "label": "Été",
        },
        wrong={"first": DATE, "last": DATE, "label": TEXT},
    ),
    "edit closure": Action(
        A + "/settings/closures/{closure_id:str}/edit",
        lambda w: {
            "first": day_of_week("monday", 7),
            "last": day_of_week("friday", 7),
            "label": "Été",
        },
        lambda w: {"closure_id": w.closure["id"]},
        wrong={"first": DATE, "last": DATE, "label": TEXT},
        ids=("closure_id",),
    ),
    "delete closure": Action(
        A + "/settings/closures/{closure_id:str}/delete",
        params=lambda w: {"closure_id": w.closure["id"]},
        ids=("closure_id",),
    ),
    "set member preference": Action(
        A + "/settings/preferences/{slot_id:str}/{user_id:str}",
        lambda w: {"value": "preferred"},
        lambda w: {"slot_id": w.slot["id"], "user_id": w.chloe_id},
        wrong={"value": VALUE},
        ids=("slot_id", "user_id"),
    ),
    "members' preferences again": Action(A + "/settings/preferences", method="GET"),
    "create share link": Action(A + "/settings/share-link"),
    "revoke share link": Action(A + "/settings/share-link/revoke"),
    # My availability
    "set my preference": Action(
        A + "/availability/preferences/{slot_id:str}",
        lambda w: {"value": "preferred"},
        lambda w: {"slot_id": w.slot["id"]},
        wrong={"value": VALUE},
        ids=("slot_id",),
    ),
    "add absence": Action(
        A + "/availability/absences",
        lambda w: {"first": day_of_week("monday", 7), "last": day_of_week("friday", 7)},
        wrong={"first": DATE, "last": DATE},
    ),
    "edit absence": Action(
        A + "/availability/absences/{absence_id:str}/edit",
        lambda w: {"first": day_of_week("monday", 7), "last": day_of_week("friday", 7)},
        lambda w: {"absence_id": w.absence["id"]},
        wrong={"first": DATE, "last": DATE},
        ids=("absence_id",),
    ),
    "delete absence": Action(
        A + "/availability/absences/{absence_id:str}/delete",
        params=lambda w: {"absence_id": w.absence["id"]},
        ids=("absence_id",),
    ),
    "set note": Action(
        A + "/availability/note", lambda w: {"text": "Evenings"}, wrong={"text": TEXT}
    ),
    # Schedule
    "more weeks": Action(
        A + "/weeks",
        lambda w: {"from": opened_weeks()["from"], "to": opened_weeks()["to"]},
        wrong={"from": DATE, "to": DATE},
    ),
    "weeks again": Action(
        A + "/weeks-again",
        lambda w: {"from": opened_weeks()["from"], "to": opened_weeks()["to"]},
        method="GET",
        wrong={"from": DATE, "to": DATE},
    ),
    "open menu": Action(
        A + "/menu", _menu_signals, wrong={"date": DATE, "start": TIME, "end": TIME}
    ),
    "sign up": Action(
        A + "/sign-up", _register_signals(4), wrong={"date": DATE, "start": TIME, "end": TIME}
    ),
    "propose": Action(
        A + "/propose",
        lambda w: {"user_id": w.chloe_id, **_register_signals(3)(w)},
        wrong={"user_id": ["not an id", 12], "date": DATE, "start": TIME, "end": TIME},
    ),
    "confirm registration": Action(
        A + "/registrations/{registration_id:str}/confirm",
        lambda w: opened_weeks(),
        lambda w: {"registration_id": w.proposed["id"]},
        ids=("registration_id",),
    ),
    "cancel registration": Action(
        A + "/registrations/{registration_id:str}/cancel",
        lambda w: opened_weeks(),
        lambda w: {"registration_id": w.own["id"]},
        ids=("registration_id",),
    ),
    # My associations
    "confirm on my associations": Action(
        A + "/summary/{registration_id:str}/confirm",
        params=lambda w: {"registration_id": w.proposed["id"]},
        ids=("registration_id",),
    ),
    "ok on my associations": Action(
        A + "/summary/{registration_id:str}/cancel",
        params=lambda w: {"registration_id": w.own["id"]},
        ids=("registration_id",),
    ),
    # Shared schedule
    "shared more weeks": Action(
        "/shared/{token:str}/weeks",
        lambda w: {"from": opened_weeks()["from"], "to": opened_weeks()["to"]},
        lambda w: {"token": w.share_token},
        user=False,
        association=False,
        wrong={"from": DATE, "to": DATE},
    ),
    "shared weeks again": Action(
        "/shared/{token:str}/weeks-again",
        lambda w: {"from": opened_weeks()["from"], "to": opened_weeks()["to"]},
        lambda w: {"token": w.share_token},
        method="GET",
        user=False,
        association=False,
        wrong={"from": DATE, "to": DATE},
    ),
}

UNSEEN = {
    "sign in",
    "sign out",
    "create account",
    "resend confirmation",
    "confirm email",
    "request password reset",
    "reset password",
    "request access link",
    "sign in by access link",
    "language",
    "notice",
    "members' preferences again",
    "more weeks",
    "weeks again",
    "open menu",
    "shared more weeks",
    "shared weeks again",
}
"""The actions whose success the snapshot of the world does not show: they change no state, or
none of its screens show."""

PAGES = {
    "/",
    "/association/new",
    A,
    A + "/members",
    A + "/settings",
    A + "/availability",
    "/shared/{token:str}",
    "/signup",
    "/verify-email",
    "/forgot-password",
    "/sign-in-link",
    "/access",
    "/reset-password",
}
"""The routes that answer a full page."""

NOT_SCREENS = {"/static/{file_path:path}"}
"""The routes that serve no screen: the static files and the schema Litestar adds."""


def _rows(keep: Callable[[Action], bool]) -> list[Any]:
    return [pytest.param(action, id=name) for name, action in ACTIONS.items() if keep(action)]


@pytest.fixture
def world(client: Any, new_client: Callable[[], Any]) -> World:
    """A world of its own, for a test whose action succeeds, its snapshot taken."""
    built = World(client, new_client)
    assert built.last
    return built


@pytest.fixture
def bare_world(client: Any, new_client: Callable[[], Any]) -> World:
    """A world of its own, for a test that looks at no snapshot."""
    return World(client, new_client)


@pytest.fixture(scope="module")
def refusing(server: Any) -> World:
    """A world shared by the tests whose action is refused: each checks that it is unchanged."""

    def open_client() -> Any:
        opened = TestClient(app=server.app)
        opened.blocking_portal = server.blocking_portal
        return opened

    built = World(open_client(), open_client)
    assert built.last
    return built


def test_every_route_is_an_action_of_the_table_or_a_page() -> None:
    declared = set()
    for route in create_app().routes:
        if route.path in NOT_SCREENS or route.path.startswith("/schema"):
            continue
        for method in getattr(route, "methods", set()) - {"OPTIONS", "HEAD"}:
            declared.add((method, route.path))
    actions = {(action.method, action.route) for action in ACTIONS.values()}
    pages = {("GET", path) for path in PAGES}

    assert actions.isdisjoint(pages)
    assert declared == actions | pages


READS = {
    "members' preferences again",
    "more weeks",
    "weeks again",
    "open menu",
    "shared more weeks",
    "shared weeks again",
}
"""The actions that only read: their refusal shows in their answer, not in the state."""


def assert_read_refused(action: Action, response: Any) -> None:
    """A refused read answers no content: a plain fragment URL fails, an action shows the
    generic error."""
    if next(name for name, row in ACTIONS.items() if row is action) not in READS:
        return
    if action.method == "GET":
        assert response.status_code >= 400, response.text
    else:
        assert GENERIC in text_of(patched(response)), response.text


def _signed_in(action: Action, world: World) -> Any:
    """The client that runs `action` signed in: Alice's or Bruno's; a client of its own for an
    action without an input `user`."""
    if not action.user:
        return world.new_client()
    return world.bruno if action.by_bruno else world.alice


# The rows themselves: each succeeds with what its screen sends, and the snapshot of the world,
# which the other tests compare, shows its success.
@pytest.mark.parametrize("action", _rows(lambda a: True))
def test_each_action_succeeds_with_what_its_screen_sends(action: Action, world: World) -> None:
    response = action.run(_signed_in(action, world), world)

    assert response.status_code in (200, 204), response.text
    assert GENERIC not in text_of(response.text)
    name = next(name for name, row in ACTIONS.items() if row is action)
    assert world.unchanged() == (name in UNSEEN)


# /core/operations/general/signed-out
# /core/operations/general/refused
# /core/ui/access/action
@pytest.mark.parametrize("action", _rows(lambda a: a.user))
def test_signed_out_an_action_leads_to_sign_in_and_changes_nothing(
    action: Action, refusing: World
) -> None:
    signals = action.signals(refusing)

    response = action.run(refusing.new_client(), refusing, signals)

    if action.method == "GET":
        assert response.status_code == 401
    else:
        assert SIGNED_OUT in shown(response)
    assert refusing.unchanged()
    if action.kept_nothing:
        action.kept_nothing(refusing, signals)


def _malformed(action: Action) -> list[tuple[str, dict[str, Any]]]:
    """Each way to send `action` an input missing, empty where it must not be, or not of its
    type."""
    return [
        (f"{name}={value!r}", {name: value})
        for name, values in action.wrong.items()
        for value in values
    ] + [(f"no {name}", {name: None}) for name in action.wrong]


BROKEN = {"add closure: no label", "edit closure: no label", "propose: user_id=12"}
"""The cases the application does not refuse yet, as /core/operations/general/malformed says:
the closure is stored without a label, and Propose answers 500."""


def _malformed_rows() -> list[Any]:
    broken = pytest.mark.xfail(
        strict=True, reason="not refused yet, as /core/operations/general/malformed says"
    )
    return [
        pytest.param(
            action,
            changes,
            id=f"{name}: {variant}",
            marks=[broken] if f"{name}: {variant}" in BROKEN else [],
        )
        for name, action in ACTIONS.items()
        for variant, changes in _malformed(action)
    ]


# /core/operations/general/malformed
# /core/operations/general/refused
@pytest.mark.parametrize(("action", "changes"), _malformed_rows())
def test_an_input_missing_or_not_of_its_type_is_refused_and_changes_nothing(
    action: Action, changes: dict[str, Any], refusing: World
) -> None:
    as_client = _signed_in(action, refusing)
    signals = action.signals(refusing)
    for name, value in changes.items():
        if value is None:
            del signals[name]
        else:
            signals[name] = value
    response = action.run(as_client, refusing, signals)

    assert response.status_code < 500, response.text
    assert refusing.unchanged()
    if None not in changes.values():
        assert_read_refused(action, response)
    if action.user:
        assert SIGNED_OUT not in response.text
    else:
        assert signed_in_as(as_client) is None
    if action.kept_nothing:
        action.kept_nothing(refusing, signals)


def _id_rows() -> list[Any]:
    return [
        pytest.param(action, name, id=f"{key}: {name}")
        for key, action in ACTIONS.items()
        for name in action.ids
    ]


# /core/operations/general/malformed
# /core/operations/general/refused
@pytest.mark.parametrize(("action", "name"), _id_rows())
def test_an_identifier_not_of_its_type_is_refused_and_changes_nothing(
    action: Action, name: str, refusing: World
) -> None:
    response = action.run(_signed_in(action, refusing), refusing, **{name: "not-an-id"})

    assert response.status_code < 500, response.text
    assert refusing.unchanged()
    assert_read_refused(action, response)


# /core/operations/general/unknown-association
# /core/operations/general/refused
@pytest.mark.parametrize("action", _rows(lambda a: a.association))
def test_an_association_that_does_not_exist_is_refused_and_changes_nothing(
    action: Action, refusing: World
) -> None:
    response = action.run(_signed_in(action, refusing), refusing, slug=unique_slug())

    assert response.status_code < 500, response.text
    assert refusing.unchanged()
    assert_read_refused(action, response)


# /core/operations/general/stays-deleted
@pytest.mark.parametrize("action", _rows(lambda a: a.user and a.method == "POST"))
def test_a_session_signed_out_while_an_action_of_it_runs_stays_deleted(
    action: Action, bare_world: World, server: Any
) -> None:
    as_client = _signed_in(action, bare_world)
    session_id = as_client.cookies["session"]
    finish = hold(server, as_client, action.path(bare_world), action.signals(bare_world))
    assert SIGNED_OUT in shown(as_client.post("/sign-out", json={}))

    finish()

    assert not stored(session_id)
    assert signed_in_as(as_client) is None
