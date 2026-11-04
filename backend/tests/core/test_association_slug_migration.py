import asyncio
import os
import re
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]
BEFORE_SLUGS = "5b7e3d1f9a24"
SLUG = re.compile(r"[a-z0-9]([a-z0-9-]{0,48}[a-z0-9])?")


async def execute(url: str, statements: list[str], autocommit: bool = False) -> None:
    engine = create_async_engine(
        url, isolation_level="AUTOCOMMIT" if autocommit else "READ COMMITTED"
    )
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))
    await engine.dispose()


def upgrade(url: str, revision: str) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "litestar",
            "--app",
            "gilda.app:create_app",
            "database",
            "upgrade",
            revision,
            "--no-prompt",
        ],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
    )


@pytest.fixture
def scratch_database() -> Iterator[str]:
    """A database of its own: the migration under test must see only these rows."""
    main = make_url(os.environ["DATABASE_URL"])
    name = f"gilda_slug_{uuid.uuid4().hex[:12]}"
    admin = main.render_as_string(hide_password=False)
    asyncio.run(execute(admin, [f'CREATE DATABASE "{name}"'], True))
    yield main.set(database=name).render_as_string(hide_password=False)
    asyncio.run(execute(admin, [f'DROP DATABASE "{name}" WITH (FORCE)'], True))


def slugs_after_migrating(url: str, names: list[str]) -> list[str]:
    """Creates associations named `names` before slugs existed, then migrates to the head."""
    upgrade(url, BEFORE_SLUGS)
    # UUIDv7-like ids, ascending, so the rows have a stable creation order.
    rows = [
        (f"00000000-0000-7000-8000-{index:012d}", name.replace("'", "''"))
        for index, name in enumerate(names)
    ]
    asyncio.run(
        execute(
            url,
            [
                f"INSERT INTO association (id, name) VALUES ('{id_}', '{name}')"
                for id_, name in rows
            ],
        )
    )
    upgrade(url, "head")

    async def read() -> list[str]:
        engine = create_async_engine(url)
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT slug FROM association ORDER BY id"))
            slugs = [row[0] for row in result]
        await engine.dispose()
        return slugs

    return asyncio.run(read())


def test_r37_derives_the_slug_from_the_name(scratch_database: str) -> None:
    slugs = slugs_after_migrating(
        scratch_database, ["Jardin partagé des Lilas", "L'Atelier  d'à côté !"]
    )

    assert slugs == ["jardin-partage-des-lilas", "l-atelier-d-a-cote"]


def test_r37_adds_a_number_when_taken(scratch_database: str) -> None:
    slugs = slugs_after_migrating(
        scratch_database, ["Atelier vélo", "Atelier vélo", "ATELIER VÉLO"]
    )

    assert sorted(slugs) == ["atelier-velo", "atelier-velo-2", "atelier-velo-3"]


def test_r37_every_slug_has_the_format_of_a_slug(scratch_database: str) -> None:
    slugs = slugs_after_migrating(
        scratch_database,
        ["a" * 60, "a" * 60, "a" * 49 + " b", "!!!", "!!!", "New", "   "],
    )

    assert len(set(slugs)) == len(slugs)
    assert "new" not in slugs
    for slug in slugs:
        assert SLUG.fullmatch(slug), slug
