from __future__ import annotations

import pytest

from test.fixtures.tables import Company
from test.sqlite.fixtures.fixtures import create_base_and_connect


@pytest.mark.asyncio
async def test_delete_one(create_base_and_connect):

    fetched = await Company.delete_where(Company.id == 2)

    assert len(fetched) == 1
    assert fetched[0].id == 2

    refetched = await Company.fetch_first(Company.id == 2)

    assert refetched == None
