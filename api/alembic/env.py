from logging.config import fileConfig
import os
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import engine_from_config, pool

try:
    from models import Base
except ImportError:
    from api.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_db_url() -> str:
    direct_database_url = os.environ.get("DATABASE_URL")
    if direct_database_url and not os.environ.get("POSTGRES_PASSWORD_FILE"):
        return direct_database_url

    user = os.environ.get("POSTGRES_USER", "user")
    db_name = os.environ.get("POSTGRES_DB", "tasks_db")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")

    password_file = os.environ.get("POSTGRES_PASSWORD_FILE", "/run/secrets/postgres_password")
    if os.path.exists(password_file):
        with open(password_file, "r", encoding="utf-8") as f:
            password = f.read().strip()
    else:
        password = os.environ.get("POSTGRES_PASSWORD")

    if not password:
        raise RuntimeError(
            "PostgreSQL password is not configured. Set POSTGRES_PASSWORD or mount docker secret."
        )

    safe_password = quote_plus(password)
    return f"postgresql://{user}:{safe_password}@{host}:{port}/{db_name}"


def run_migrations_offline() -> None:
    url = get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config.set_main_option("sqlalchemy.url", get_db_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
