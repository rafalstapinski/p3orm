from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from asyncpg import Connection, Pool

from p3orm.core import postgres
from p3orm.exceptions import AlreadyConnected, NotConnected

from test.fixtures.helpers import _get_connection_kwargs, create_base
from test.fixtures.tables import Company

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_connection(postgresql: connection):

    db = postgres()
    await db.connect(**_get_connection_kwargs(postgresql))

    assert db.is_connected() == True
    assert isinstance(db.connection, Connection)
    assert db.connection.is_closed() == False
    assert db.pool == None

    await db.disconnect()

    assert db.is_connected() == False
    assert db.connection == None
    assert db.pool == None


@pytest.mark.asyncio
async def test_pool(postgresql: connection):

    db = postgres()
    await db.connect_pool(**_get_connection_kwargs(postgresql))

    assert db.is_connected() == True
    assert isinstance(db.pool, Pool)
    assert db.pool._closed == False
    assert db.connection == None

    await db.disconnect()
    assert db.is_connected() == False
    assert db.connection == None
    assert db.pool == None


@pytest.mark.asyncio
async def test_cant_connect_with_both(postgresql: connection):

    db = postgres()
    await db.connect(**_get_connection_kwargs(postgresql))

    with pytest.raises(AlreadyConnected):
        await db.connect_pool(**_get_connection_kwargs(postgresql))

    await db.disconnect()

    await db.connect_pool(**_get_connection_kwargs(postgresql))

    with pytest.raises(AlreadyConnected):
        await db.connect(**_get_connection_kwargs(postgresql))

    await db.disconnect()


@pytest.mark.asyncio
async def test_exception_when_not_connected(postgresql: connection):

    create_base(postgresql)

    with pytest.raises(NotConnected):
        await Company.fetch_all()
