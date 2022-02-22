from __future__ import annotations

from datetime import datetime

import pytest

from p3orm.exceptions import MultipleResultsReturned, NoResultsReturned

from test.fixtures.helpers import create_base_and_connect
from test.fixtures.tables import Company


@pytest.mark.asyncio
async def test_fetch_all(create_base_and_connect):

    companies = await Company.fetch_all()

    assert len(companies) == 4
    assert [c.id for c in companies] == [1, 2, 3, 4]
    assert [c.name for c in companies] == ["Company 1", "Company 2", "Company 3", "Company 4"]
    assert [isinstance(c.created_at, datetime) for c in companies] == [True] * 4


@pytest.mark.asyncio
async def test_fetch_all_filtering(create_base_and_connect):

    companies = await Company.fetch_all(Company.id < 3)

    assert len(companies) == 2
    assert [c.id for c in companies] == [1, 2]
    assert [c.name for c in companies] == ["Company 1", "Company 2"]
    assert [isinstance(c.created_at, datetime) for c in companies] == [True] * 2


@pytest.mark.asyncio
async def test_fetch_first(create_base_and_connect):

    company = await Company.fetch_first(Company.id < 3)

    assert company.id == 1
    assert company.name == "Company 1"
    assert isinstance(company.created_at, datetime)


@pytest.mark.asyncio
async def test_fetch_first(create_base_and_connect):

    company = await Company.fetch_first(Company.id == 1)

    assert company.id == 1
    assert company.name == "Company 1"
    assert isinstance(company.created_at, datetime)


@pytest.mark.asyncio
async def test_fetch_one(create_base_and_connect):

    assert await Company.fetch_one(Company.id == 1) == await Company.fetch_first(Company.id == 1)


@pytest.mark.asyncio
async def test_fetch_one_fails_with_multiple(create_base_and_connect):

    with pytest.raises(MultipleResultsReturned):
        await Company.fetch_one(Company.id != 1)


@pytest.mark.asyncio
async def test_fetch_one_fails_with_none(create_base_and_connect):

    with pytest.raises(NoResultsReturned):
        await Company.fetch_one(Company.id == 100)


@pytest.mark.asyncio
async def test_fetch_first_returns_none(create_base_and_connect):

    result = await Company.fetch_first(Company.id == 100)

    assert result == None


@pytest.mark.asyncio
async def test_fetch_all_returns_empty(create_base_and_connect):

    results = await Company.fetch_all(Company.id == 100)

    assert results == []
