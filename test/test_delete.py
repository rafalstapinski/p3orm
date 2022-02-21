from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg
import pytest

from test.fixtures.helpers import create_base_and_connect
from test.fixtures.tables import Company

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_update_one(postgresql: connection):

    await create_base_and_connect(postgresql)

    fetched = await Company.delete_where(Company.id == 2)

    assert len(fetched) == 1
    assert fetched[0].id == 2

    refetched = await Company.fetch_first(Company.id == 2)

    assert refetched == None
