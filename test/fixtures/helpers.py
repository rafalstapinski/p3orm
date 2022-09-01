from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from p3orm.core import postgres

if TYPE_CHECKING:
    from psycopg2 import connection

from test.fixtures.queries import BASE_DATA, BASE_TABLES


def create_base_tables(postgresql: connection):

    cursor = postgresql.cursor()
    cursor.execute(BASE_TABLES)
    postgresql.commit()
    cursor.close()


def create_base_data(postgresql: connection):

    cursor = postgresql.cursor()
    cursor.execute(BASE_DATA)
    postgresql.commit()
    cursor.close()


def create_base(postgresql: connection):
    create_base_tables(postgresql)
    create_base_data(postgresql)


@pytest.fixture(scope="function")
async def create_base_and_connect(postgresql: connection):
    create_base(postgresql)
    dsn_params = postgresql.get_dsn_parameters()

    db = postgres()
    await db.connect(
        user=dsn_params.get("user"),
        password=dsn_params.get("password"),
        database=dsn_params.get("dbname"),
        host=dsn_params.get("host"),
        port=dsn_params.get("port"),
    )

    yield

    await db.disconnect()


def _get_connection_kwargs(postgresql: connection):
    dsn_params = postgresql.get_dsn_parameters()
    return dict(
        user=dsn_params.get("user"),
        password=dsn_params.get("password"),
        database=dsn_params.get("dbname"),
        host=dsn_params.get("host"),
        port=dsn_params.get("port"),
    )
