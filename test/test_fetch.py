from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from p3orm.exceptions import MultipleResultsReturned, NoResultsReturned

from test.fixtures.helpers import create_base_and_connect
from test.fixtures.tables import Company

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_fetch_all(postgresql: connection):

    await create_base_and_connect(postgresql)

    companies = await Company.fetch_all()

    assert len(companies) == 4
    assert [c.id for c in companies] == [1, 2, 3, 4]
    assert [c.name for c in companies] == ["Company 1", "Company 2", "Company 3", "Company 4"]
    assert [isinstance(c.created_at, datetime) for c in companies] == [True] * 4


@pytest.mark.asyncio
async def test_fetch_many_filtering(postgresql: connection):

    await create_base_and_connect(postgresql)

    companies = await Company.fetch_many(Company.id < 3)

    assert len(companies) == 2
    assert [c.id for c in companies] == [1, 2]
    assert [c.name for c in companies] == ["Company 1", "Company 2"]
    assert [isinstance(c.created_at, datetime) for c in companies] == [True] * 2


@pytest.mark.asyncio
async def test_fetch_first(postgresql: connection):

    await create_base_and_connect(postgresql)

    company = await Company.fetch_first(Company.id < 3)

    assert company.id == 1
    assert company.name == "Company 1"
    assert isinstance(company.created_at, datetime)


@pytest.mark.asyncio
async def test_fetch_first(postgresql: connection):

    await create_base_and_connect(postgresql)

    company = await Company.fetch_first(Company.id == 1)

    assert company.id == 1
    assert company.name == "Company 1"
    assert isinstance(company.created_at, datetime)


@pytest.mark.asyncio
async def test_fetch_one(postgresql: connection):

    await create_base_and_connect(postgresql)

    assert await Company.fetch_one(Company.id == 1) == await Company.fetch_first(Company.id == 1)


@pytest.mark.asyncio
async def test_fetch_one_fails_with_multiple(postgresql: connection):

    await create_base_and_connect(postgresql)

    with pytest.raises(MultipleResultsReturned):
        await Company.fetch_one(Company.id != 1)


@pytest.mark.asyncio
async def test_fetch_one_fails_with_none(postgresql: connection):

    await create_base_and_connect(postgresql)

    with pytest.raises(NoResultsReturned):
        await Company.fetch_one(Company.id == 100)


@pytest.mark.asyncio
async def fetch_first_returns_none(postgresql: connection):

    await create_base_and_connect(postgresql)

    result = await Company.fetch_first(Company.id == 100)

    assert result == None


@pytest.mark.asyncio
async def fetch_many_returns_empty(postgresql: connection):

    await create_base_and_connect(postgresql)

    results = await Company.fetch_many(Company.id == 100)

    assert results == []
