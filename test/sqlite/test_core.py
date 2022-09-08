from __future__ import annotations

import pytest

# from test.sqlite.fixture.helpers import
from aiosqlite.core import Connection

from p3orm.core import sqlite
from p3orm.exceptions import NotConnected

from test.fixtures.tables import Company
from test.sqlite.fixtures.fixtures import sqlite_base


@pytest.mark.asyncio
async def test_connection():

    db = sqlite()
    await db.connect(":memory:")

    assert db.is_connected() == True
    assert isinstance(db.connection, Connection)
    assert db.connection._running == True

    await db.disconnect()

    assert db.is_connected() == False
    assert db.connection == None


@pytest.mark.asyncio
async def test_exception_when_not_connected(sqlite_base):

    with pytest.raises(NotConnected):
        await Company.fetch_all()
