from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from asyncpg import Connection, Pool

from p3orm.core import Porm
from p3orm.exceptions import AlreadyConnected, NotConnected

from test.fixtures.helpers import _get_connection_kwargs, create_base
from test.fixtures.tables import Company

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_connection(postgresql: connection):

    await Porm.connect(**_get_connection_kwargs(postgresql))

    assert Porm.is_connected() == True
    assert isinstance(Porm.connection, Connection)
    assert Porm.connection.is_closed() == False
    assert Porm.pool == None

    await Porm.disconnect()

    assert Porm.is_connected() == False
    assert Porm.connection == None
    assert Porm.pool == None


@pytest.mark.asyncio
async def test_pool(postgresql: connection):

    await Porm.connect_pool(**_get_connection_kwargs(postgresql))

    assert Porm.is_connected() == True
    assert isinstance(Porm.pool, Pool)
    assert Porm.pool._closed == False
    assert Porm.connection == None

    await Porm.disconnect()

    assert Porm.is_connected() == False
    assert Porm.connection == None
    assert Porm.pool == None


@pytest.mark.asyncio
async def test_cant_connect_with_both(postgresql: connection):

    await Porm.connect(**_get_connection_kwargs(postgresql))

    with pytest.raises(AlreadyConnected):
        await Porm.connect_pool(**_get_connection_kwargs(postgresql))

    await Porm.disconnect()

    await Porm.connect_pool(**_get_connection_kwargs(postgresql))

    with pytest.raises(AlreadyConnected):
        await Porm.connect(**_get_connection_kwargs(postgresql))

    await Porm.disconnect()


@pytest.mark.asyncio
async def test_exception_when_not_connected(postgresql: connection):

    create_base(postgresql)

    with pytest.raises(NotConnected):
        await Company.fetch_all()
