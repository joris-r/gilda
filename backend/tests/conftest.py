import os
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from argon2 import PasswordHasher
from litestar.testing import TestClient

from gilda.app import create_app

DEFAULT_DATABASE_URL = "postgresql+asyncpg://gilda:gilda@localhost:15432/gilda_test"

os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)

# The host clock is not in the associations' timezone, as on the hosting provider.
os.environ["TZ"] = "UTC"
time.tzset()

BACKEND_DIR = Path(__file__).resolve().parent.parent


def pytest_configure(config: pytest.Config) -> None:
    # Under pytest-xdist, only the controller migrates, before the workers start.
    if hasattr(config, "workerinput"):
        return
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
    # Mailpit keeps every email (no cap to prune), so each run starts it empty.
    mailpit_url = os.environ.get("MAILPIT_URL", "http://localhost:18025")
    httpx.delete(f"{mailpit_url}/api/v1/messages").raise_for_status()


@pytest.fixture(scope="session", autouse=True)
def cheap_password_hashing() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "gilda.core.services._hasher",
            PasswordHasher(time_cost=1, memory_cost=8, parallelism=1),
        )
        yield


@pytest.fixture(scope="session")
def server() -> Iterator[Any]:
    """The application of this worker, started once, with its event loop."""
    with TestClient(app=create_app()) as started:
        yield started
