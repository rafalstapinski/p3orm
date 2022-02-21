from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from p3orm.core import Porm

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_connection(postgresql: connection):

    dsn_params = postgresql.get_dsn_parameters()

    await Porm.connect(
        user=dsn_params.get("user"),
        password=dsn_params.get("password"),
        database=dsn_params.get("dbname"),
        host=dsn_params.get("host"),
        port=dsn_params.get("port"),
    )
    assert Porm.connection.is_closed() == False

    await Porm.disconnect()
    assert Porm.connection.is_closed() == True
