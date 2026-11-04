"""association slug

Revision ID: 3f8a6c2e7d41
Revises: 5b7e3d1f9a24
Create Date: 2026-11-04 12:00:00.000000

"""

import re
import unicodedata
import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import (
    GUID,
    ORA_JSONB,
    Bool,
    DateTimeUTC,
    EncryptedString,
    EncryptedText,
    FernetBackend,
    JsonB,
    OneTimeCode,
    PasswordHash,
    StoredObject,
    TOTPSecret,
)
from advanced_alchemy.types.encrypted_string import PGCryptoBackend
from advanced_alchemy.types.password_hash.argon2 import Argon2Hasher
from advanced_alchemy.types.password_hash.passlib import PasslibHasher
from advanced_alchemy.types.password_hash.pwdlib import PwdlibHasher
from alembic import op
from sqlalchemy import Text  # noqa: F401

if TYPE_CHECKING:
    pass

__all__ = (
    "data_downgrades",
    "data_upgrades",
    "downgrade",
    "schema_downgrades",
    "schema_upgrades",
    "upgrade",
)

sa.GUID = GUID
sa.Bool = Bool
sa.DateTimeUTC = DateTimeUTC
sa.JsonB = JsonB
sa.ORA_JSONB = ORA_JSONB
sa.EncryptedString = EncryptedString
sa.EncryptedText = EncryptedText
sa.StoredObject = StoredObject
sa.PasswordHash = PasswordHash
sa.Argon2Hasher = Argon2Hasher
sa.PasslibHasher = PasslibHasher
sa.PwdlibHasher = PwdlibHasher
sa.FernetBackend = FernetBackend
sa.PGCryptoBackend = PGCryptoBackend
sa.TOTPSecret = TOTPSecret
sa.OneTimeCode = OneTimeCode

# revision identifiers, used by Alembic.
revision = "3f8a6c2e7d41"
down_revision = "5b7e3d1f9a24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()


def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()


MAX_LENGTH = 50


def slug_base(name: str) -> str:
    """The association's name as New association turns it into a slug (R35)."""
    decomposed = unicodedata.normalize("NFD", name)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", plain).strip("-")[:MAX_LENGTH].rstrip("-")
    return slug or "association"


def free_slug(base: str, taken: set[str]) -> str:
    """`base`, followed by the first number that makes it free, still within the length."""
    slug, number = base, 1
    while slug in taken:
        number += 1
        suffix = f"-{number}"
        slug = base[: MAX_LENGTH - len(suffix)].rstrip("-") + suffix
    return slug


def schema_upgrades() -> None:
    """schema upgrade migrations go here."""
    op.add_column("association", sa.Column("slug", sa.String(length=50), nullable=True))
    # R37; `new` is never a slug.
    connection = op.get_bind()
    taken = {"new"}
    for id_, name in connection.execute(
        sa.text("SELECT id, name FROM association ORDER BY id")
    ).all():
        slug = free_slug(slug_base(name), taken)
        taken.add(slug)
        connection.execute(
            sa.text("UPDATE association SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": id_},
        )
    op.alter_column("association", "slug", nullable=False)
    op.create_unique_constraint(op.f("uq_association_slug"), "association", ["slug"])


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    op.drop_constraint(op.f("uq_association_slug"), "association", type_="unique")
    op.drop_column("association", "slug")


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
