import sqlite3

import pytest

from p3orm import sqlite

from test.fixtures.queries import BASE_DATA, BASE_TABLES_SQLITE


@pytest.fixture
def sqlite_base():
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()

    for query in BASE_TABLES_SQLITE.split(";\n"):
        cursor.execute(query)
        connection.commit()

    for query in BASE_DATA.split(";\n"):
        cursor.execute(query)
        connection.commit()

    yield cursor

    connection.close()


@pytest.fixture
async def create_base_and_connect():

    db = sqlite()
    await db.connect(":memory:")

    for query in BASE_TABLES_SQLITE.split(";\n"):
        await db.connection.execute(query)
        await db.connection.commit()

    for query in BASE_DATA.split(";\n"):
        await db.connection.execute(query)
        await db.connection.commit()

    yield db

    await db.disconnect()
