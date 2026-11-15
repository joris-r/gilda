"""Fails when a Datastar backend action in the templates may be sent again on its own.

Each `@post(...)`, `@get(...)`, `@put(...)`, `@patch(...)` or `@delete(...)` must set
`retryMaxCount: 0`, so that a request that failed is not resent by Datastar.
"""

import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "gilda"
ACTION = re.compile(r"@(?:post|get|put|patch|delete)\(")
ONCE = re.compile(r"\bretryMaxCount:\s*0\b")


def action_at(text: str, start: int) -> str:
    """The text of the action whose opening parenthesis ends at `start`, up to its closing one."""
    depth = 1
    for end in range(start, len(text)):
        if text[end] == "(":
            depth += 1
        elif text[end] == ")":
            depth -= 1
            if depth == 0:
                return text[start:end]
    return text[start:]


def main() -> int:
    failures = []
    for path in sorted(TEMPLATES.glob("**/templates/**/*.html")):
        text = path.read_text(encoding="utf-8")
        for match in ACTION.finditer(text):
            if not ONCE.search(action_at(text, match.end())):
                line = text.count("\n", 0, match.start()) + 1
                where = f"{path.relative_to(TEMPLATES)}:{line}"
                failures.append(f"{where}: {match.group()} without retryMaxCount: 0")
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
