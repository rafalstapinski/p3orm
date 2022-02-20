from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import asyncpg
import pytest

from test.fixtures.helpers import create_base_and_connect
from test.fixtures.tables import Company

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_insert_one(postgresql: connection):

    await create_base_and_connect(postgresql)

    to_insert = Company(name="Company 5")

    created = await Company.insert_one(to_insert)
    fetched = await Company.fetch_one(Company.name == "Company 5")

    assert created == fetched


@pytest.mark.asyncio
async def test_insert_one_fails_null(postgresql: connection):

    await create_base_and_connect(postgresql)

    to_insert = Company()

    with pytest.raises(asyncpg.exceptions.NotNullViolationError):
        await Company.insert_one(to_insert)


@pytest.mark.asyncio
async def test_insert_one_ignores_autogen(postgresql: connection):

    await create_base_and_connect(postgresql)

    to_insert = Company(id=999, name="Company 5", created_at=datetime.utcnow())

    await Company.insert_one(to_insert)
    fetched = await Company.fetch_one(Company.name == "Company 5")

    assert to_insert.name == fetched.name
    assert to_insert.id != fetched.id
    assert to_insert.created_at != fetched.created_at


@pytest.mark.asyncio
async def test_insert_many(postgresql: connection):

    await create_base_and_connect(postgresql)

    to_insert = [Company(name="Company 5"), Company(name="Company 6"), Company(name="Company 7")]

    created = await Company.insert_many(to_insert)
    fetched = await Company.fetch_many(Company.id.isin([5, 6, 7]))

    assert created == fetched


@pytest.mark.asyncio
async def test_insert_many_fails_null(postgresql: connection):

    await create_base_and_connect(postgresql)

    to_insert = [Company(), Company()]

    with pytest.raises(asyncpg.exceptions.NotNullViolationError):
        await Company.insert_many(to_insert)


@pytest.mark.asyncio
async def test_insert_many_ignores_autogen(postgresql: connection):

    await create_base_and_connect(postgresql)

    to_insert = [
        Company(id=998, name="Company 5", created_at=datetime.utcnow()),
        Company(id=999, name="Company 5", created_at=datetime.utcnow()),
    ]

    created = await Company.insert_many(to_insert)

    assert to_insert[0].id != created[0].id
    assert to_insert[1].id != created[1].id

    assert to_insert[0].created_at != created[0].created_at
    assert to_insert[1].created_at != created[1].created_at

    assert to_insert[0].name == created[0].name
    assert to_insert[1].name == created[1].name