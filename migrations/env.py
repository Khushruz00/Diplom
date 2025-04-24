import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 📌 Добавляем путь к корню проекта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 📦 Импорт конфигурации и моделей
from Diplom.config import DevelopmentConfig
from Diplom.models import db

# Alembic Config объект
config = context.config

# ✅ Устанавливаем правильный URL к БД из Flask config
config.set_main_option("sqlalchemy.url", DevelopmentConfig.SQLALCHEMY_DATABASE_URI)

# Логгинг конфигурации
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 📌 Указываем metadata
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в офлайн-режиме (без подключения к БД)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в онлайн-режиме (с подключением к БД)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# 🔁 Выбор режима
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
