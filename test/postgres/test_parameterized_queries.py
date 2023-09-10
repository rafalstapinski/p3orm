import pytest

from test.fixtures.tables import Company
from test.postgres.fixtures.helpers import create_base_and_connect


@pytest.mark.asyncio
async def test_between(create_base_and_connect):
    companies = await Company.fetch_all(Company.id.between(1, 3))

    assert len(companies) == 3
    assert companies[0].id == 1
    assert companies[1].id == 2
    assert companies[2].id == 3


@pytest.mark.asyncio
async def test_isin(create_base_and_connect):
    companies = await Company.fetch_all(Company.name.isin(["Company 1", "Company 2"]))

    assert len(companies) == 2
    assert companies[0].id == 1
    assert companies[1].id == 2
