import os

DEFAULT_DATABASE_URL = "postgresql+asyncpg://gilda:gilda@localhost:5432/gilda"

os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
