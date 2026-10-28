import os

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    EngineConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)

CONNECT_TIMEOUT_SECONDS = 2


def create_database_config() -> SQLAlchemyAsyncConfig:
    return SQLAlchemyAsyncConfig(
        connection_string=os.environ["DATABASE_URL"],
        engine_config=EngineConfig(connect_args={"timeout": CONNECT_TIMEOUT_SECONDS}),
        alembic_config=AlembicAsyncConfig(script_location="migrations"),
        before_send_handler="autocommit",
    )


def create_database_plugin(config: SQLAlchemyAsyncConfig) -> SQLAlchemyPlugin:
    return SQLAlchemyPlugin(config=config)
