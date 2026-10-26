import os

from alembic import context
from sqlalchemy import create_engine, pool

from woodshed.models import Base

url = context.config.get_main_option("sqlalchemy.url") or os.environ["DATABASE_URL"]

with create_engine(url, poolclass=pool.NullPool).connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
