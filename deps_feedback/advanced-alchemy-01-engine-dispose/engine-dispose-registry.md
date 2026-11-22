Title: SQLAlchemyAsyncConfig lifespan disposes only the first config's engine per process

Version: advanced-alchemy 1.12.0 (same code in 1.13.0b2), Litestar 2.25, Python 3.13.

When a process creates more than one `SQLAlchemyAsyncConfig` (e.g. a test suite that builds one Litestar app per test client), `__post_init__` renames the state keys through `_ensure_unique`: the second config gets `engine_app_state_key = "db_engine_1"`, the third `"db_engine_2"`, and so on. But `lifespan()` disposes the engine it finds under `engine_dependency_key`, which stays `"db_engine"`:

```python
deps = self.create_app_state_items()   # keyed by engine_app_state_key ("db_engine_1")
...
finally:
    if self.engine_dependency_key in deps:   # "db_engine": not in deps
        ...dispose()
```

So from the second config on, the engine is never disposed at shutdown, and its connections stay open until the process ends.

A second effect of the same registry: `_ensure_unique` recurses once per key already taken, and the class-level registries never shrink, so after several hundred configs in one process (about 330 under pytest, about 1,000 in a bare script) `__post_init__` raises `RecursionError: maximum recursion depth exceeded`.

Reproduction:

```python
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig
configs = [SQLAlchemyAsyncConfig(connection_string="postgresql+asyncpg://user@localhost/db") for _ in range(2)]
print(configs[1].engine_app_state_key, configs[1].engine_dependency_key)  # db_engine_1 db_engine
# for _ in range(1200): SQLAlchemyAsyncConfig(connection_string="postgresql+asyncpg://user@localhost/db")  -> RecursionError
```

Suggested fix: in `lifespan()`, look the engine up under `self.engine_app_state_key` (the key `create_app_state_items()` uses); and make `_ensure_unique` iterative.

## How Gilda avoids it

Not for upstream: how this project lives with the bug.

- The backend test suite builds the application once per pytest-xdist
  worker (the session fixture `server` in `backend/tests/conftest.py`).
  Every test client runs on that one app, so each process creates a
  single `SQLAlchemyAsyncConfig`. Its keys keep their names, its engine
  is disposed, and the registry does not grow.
- A test may build another app only if it never runs its lifespan
  (as the route listing in `tests/planning/test_general_rules.py`
  does): a second app whose lifespan runs leaves its engine open.
- Once fixed upstream, the one app per worker stays: it was chosen for
  the suite's speed too.
