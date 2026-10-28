import os

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    EngineConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)

CONNECT_TIMEOUT_SECONDS = 2


def create_database_plugin() -> SQLAlchemyPlugin:
    config = SQLAlchemyAsyncConfig(
        connection_string=os.environ["DATABASE_URL"],
        engine_config=EngineConfig(connect_args={"timeout": CONNECT_TIMEOUT_SECONDS}),
        alembic_config=AlembicAsyncConfig(script_location="migrations"),
    )
    return SQLAlchemyPlugin(config=config)
