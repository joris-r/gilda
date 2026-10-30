import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

DEFAULT_DATABASE_URL = "postgresql+asyncpg://gilda:gilda@localhost:5432/gilda"

os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)

# The host clock is not in the associations' timezone, as on the hosting provider.
os.environ["TZ"] = "UTC"
time.tzset()

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "litestar",
            "--app",
            "gilda.app:create_app",
            "database",
            "upgrade",
            "--no-prompt",
        ],
        cwd=BACKEND_DIR,
        check=True,
        capture_output=True,
    )
