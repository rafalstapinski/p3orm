from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from test.fixtures.helpers import create_base_and_connect
from test.fixtures.tables import Company

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_update_one(postgresql: connection):

    await create_base_and_connect(postgresql)

    fetched = await Company.fetch_one(Company.id == 1)

    fetched.name = "Company Name Changed"

    updated = await Company.update_one(fetched)

    assert updated == fetched
    assert updated.name == "Company Name Changed"

    fetched.name = "name changed locally without commiting to database"

    assert updated != fetched
