"""Reading HTML as the browser shows it: through an HTML parser, only the elements shown, their
text unescaped.

An element is not shown when it is a `script`, `style`, `template` or `head`, has the `hidden`
attribute or `display: none` in its style, or is a closed dialog or popover. The elements at the
top of a fragment count as open: a test that reads a dialog, or the patch of a menu, chose it."""

import re
from collections.abc import Callable, Iterator
from html import escape
from html.parser import HTMLParser

_VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}
_BLOCKS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "details",
    "dialog",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "option",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
"""The elements that show apart from the text around them; the others run on with it."""
_NEVER_SHOWN = {"script", "style", "template", "head"}


class Element:
    """An element of a parsed piece of HTML, or the root of it (tag "")."""

    def __init__(self, tag: str, attrs: dict[str, str | None], parent: "Element | None") -> None:
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Element | str] = []

    def __repr__(self) -> str:
        return self.html

    def get(self, name: str) -> str | None:
        return self.attrs.get(name)

    def has(self, name: str) -> bool:
        return name in self.attrs

    @property
    def classes(self) -> list[str]:
        return (self.get("class") or "").split()

    def is_shown(self) -> bool:
        """Whether the element shows, its ancestors aside; at the top of a fragment, a dialog or a
        popover counts as open."""
        if self.tag in _NEVER_SHOWN or self.has("hidden"):
            return False
        if re.search(r"display:\s*none", self.get("style") or ""):
            return False
        at_top = self.parent is not None and self.parent.tag == ""
        closable = self.tag == "dialog" or self.has("popover")
        return at_top or not closable or self.has("open")

    def elements(self, tag: str | None = None, *, hidden: bool = False) -> Iterator["Element"]:
        """The descendants shown, in document order, or all of them with `hidden`; only those of
        `tag` when given."""
        for child in self.children:
            if isinstance(child, str) or not (hidden or child.is_shown()):
                continue
            if tag is None or child.tag == tag:
                yield child
            yield from child.elements(tag, hidden=hidden)

    def first(self, tag: str, *, hidden: bool = False) -> "Element":
        """The first descendant of `tag`, shown unless `hidden`."""
        found = next(self.elements(tag, hidden=hidden), None)
        assert found is not None, f"no {tag} in {self.html}"
        return found

    def outermost(self, tag: str) -> list["Element"]:
        """The descendants of `tag` shown, leaving out those within another one."""
        found: list[Element] = []
        for child in self.children:
            if isinstance(child, str) or not child.is_shown():
                continue
            if child.tag == tag:
                found.append(child)
            else:
                found.extend(child.outermost(tag))
        return found

    def text_with(self, rewrite: Callable[["Element"], str | None]) -> str:
        """What the element shows, its spaces collapsed, where `rewrite` gives the text of each
        descendant it does not answer None for."""
        pieces: list[str] = []

        def walk(element: Element) -> None:
            for child in element.children:
                if isinstance(child, str):
                    pieces.append(child)
                elif child.is_shown():
                    replaced = rewrite(child)
                    apart = " " if child.tag in _BLOCKS or replaced is not None else ""
                    pieces.append(apart)
                    if replaced is None:
                        walk(child)
                    else:
                        pieces.append(replaced)
                    pieces.append(apart)

        walk(self)
        return collapsed("".join(pieces))

    @property
    def text(self) -> str:
        """What the element shows, its spaces collapsed, a block apart from the text around."""
        return self.text_with(lambda _: None)

    @property
    def html(self) -> str:
        """The element as HTML, with only the descendants shown."""
        if not self.tag:
            return self.inner_html
        attributes = "".join(
            f" {name}" if value is None else f' {name}="{escape(value)}"'
            for name, value in self.attrs.items()
        )
        if self.tag in _VOID:
            return f"<{self.tag}{attributes}>"
        return f"<{self.tag}{attributes}>{self.inner_html}</{self.tag}>"

    @property
    def inner_html(self) -> str:
        return "".join(
            escape(child, quote=False) if isinstance(child, str) else child.html
            for child in self.children
            if isinstance(child, str) or child.is_shown()
        )


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("", {}, None)
        self.current = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, dict(attrs), self.current)
        self.current.children.append(element)
        if tag not in _VOID:
            self.current = element

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current.children.append(Element(tag, dict(attrs), self.current))

    def handle_endtag(self, tag: str) -> None:
        open_element: Element | None = self.current
        while open_element is not None and open_element.tag != tag:
            open_element = open_element.parent
        if open_element is not None and open_element.parent is not None:
            self.current = open_element.parent

    def handle_data(self, data: str) -> None:
        self.current.children.append(data)


def collapsed(text: str) -> str:
    """`text` with each run of spaces, tabs and line breaks as one space, as the browser shows
    it, and none at its ends."""
    return re.sub(r"[ \t\n\r\f]+", " ", text).strip(" ")


def parse(fragment: str) -> Element:
    """The root of a piece of HTML: a page, a part of it or a patch."""
    parser = _Parser()
    parser.feed(fragment)
    parser.close()
    return parser.root


def text_of(fragment: str) -> str:
    """What a piece of HTML shows, its spaces collapsed."""
    return parse(fragment).text


def part(page: str, tag: str) -> str:
    """The HTML of the first `tag` the page shows, with only what it shows."""
    return parse(page).first(tag).html


def lines_of(fragment: str) -> list[str]:
    """The text of each list item a piece of HTML shows, a nested list within its item."""
    return [item.text for item in parse(fragment).outermost("li")]


def heading_of(fragment: str) -> str:
    """The text of the first `h1` a piece of HTML shows."""
    return parse(fragment).first("h1").text


def dialogs_named(page: str, name: str) -> list[Element]:
    """The dialogs of the page, open or not, whose accessible name is `name`: their
    `aria-label`, or the text of the element their `aria-labelledby` names, or else of their
    first heading. Each stands at the top of a fragment of its own, so that it reads open."""
    root = parse(page)
    by_id = {e.get("id"): e for e in root.elements(hidden=True) if e.get("id")}

    def name_of(dialog: Element) -> str:
        if dialog.get("aria-label"):
            return collapsed(dialog.get("aria-label") or "")
        labelled = by_id.get(dialog.get("aria-labelledby"))
        if labelled is not None:
            return labelled.text
        heading = next((e for e in dialog.elements() if re.fullmatch(r"h[1-6]", e.tag)), None)
        return heading.text if heading is not None else ""

    dialogs = [_detached(dialog) for dialog in root.elements("dialog", hidden=True)]
    return [dialog for dialog in dialogs if name_of(dialog) == name]


def dialog_named(page: str, name: str) -> Element:
    """The one dialog of the page whose accessible name is `name`, as `dialogs_named` finds it."""
    found = dialogs_named(page, name)
    assert len(found) == 1, f"{len(found)} dialogs named {name}"
    return found[0]


def _detached(element: Element) -> Element:
    """`element` at the top of a fragment of its own, so that it counts as open."""
    root = Element("", {}, None)
    copy = Element(element.tag, element.attrs, root)
    copy.children = element.children
    root.children = [copy]
    return copy


def buttons_named(fragment: str, name: str) -> list[Element]:
    """The buttons a piece of HTML shows whose accessible name is `name`: their `aria-label`, or
    else their text."""
    return [
        button
        for button in parse(fragment).elements("button")
        if collapsed(button.get("aria-label") or button.text) == name
    ]


def dialog_opened_by(page: str, button: Element) -> Element:
    """The dialog of the page that `button` opens, by its `commandfor`, at the top of a fragment
    of its own."""
    assert button.get("command") == "show-modal", button
    target = button.get("commandfor")
    found = [d for d in parse(page).elements("dialog", hidden=True) if d.get("id") == target]
    assert len(found) == 1, f"{len(found)} dialogs {target}"
    return _detached(found[0])
