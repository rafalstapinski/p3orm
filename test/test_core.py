from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from p3orm.core import Porm

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_connection(postgresql: connection):

    await Porm.connect(**postgresql.get_dsn_parameters())
    assert Porm.connection.is_closed() == False

    await Porm.disconnect()
    assert Porm.connection.is_closed() == True
