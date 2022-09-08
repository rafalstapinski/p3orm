from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest
from pydantic import ValidationError

from test.fixtures.tables import Company, Employee
from test.sqlite.fixtures.fixtures import create_base_and_connect


@pytest.mark.asyncio
async def test_insert_one(create_base_and_connect):

    to_insert = Company(name="Company 5")

    created = await Company.insert_one(to_insert)
    fetched = await Company.fetch_one(Company.name == "Company 5")

    assert created == fetched


@pytest.mark.asyncio
async def test_insert_one_fails_null(create_base_and_connect):

    with pytest.raises(ValidationError):
        to_insert = Company()

    with pytest.raises(sqlite3.IntegrityError):
        to_insert = Company(name="ok")
        to_insert.name = None
        await Company.insert_one(to_insert)


@pytest.mark.asyncio
async def test_insert_one_ignores_autogen(create_base_and_connect):

    to_insert = Company(id=999, name="Company 5", created_at=datetime.utcnow())

    await Company.insert_one(to_insert)
    fetched = await Company.fetch_one(Company.name == "Company 5")

    assert to_insert.name == fetched.name
    assert to_insert.id != fetched.id
    assert to_insert.created_at != fetched.created_at


@pytest.mark.asyncio
async def test_insert_many(create_base_and_connect):

    to_insert = [Company(name="Company 5"), Company(name="Company 6"), Company(name="Company 7")]

    created = await Company.insert_many(to_insert)
    fetched = await Company.fetch_all(Company.id.isin([5, 6, 7]))

    assert created == fetched


@pytest.mark.asyncio
async def test_insert_many_fails_null(create_base_and_connect):

    with pytest.raises(sqlite3.IntegrityError):
        to_insert = [Company(name="ok"), Company(name="ok2")]
        to_insert[0].name = None
        await Company.insert_many(to_insert)


@pytest.mark.asyncio
async def test_insert_many_ignores_autogen(create_base_and_connect):

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


@pytest.mark.asyncio
async def test_insert_one_prefetch(create_base_and_connect):

    company = await Company.fetch_one(Company.id == 1)
    to_insert = Employee(name="Person", company_id=company.id)

    created = await Employee.insert_one(to_insert, prefetch=[[Employee.company]])

    assert created.company == company


@pytest.mark.asyncio
async def test_insert_many_prefetch(create_base_and_connect):

    company = await Company.fetch_one(Company.id == 1)
    to_insert = [Employee(name="Person", company_id=company.id), Employee(name="Person", company_id=company.id)]

    created = await Employee.insert_many(to_insert, prefetch=[[Employee.company]])

    for employee in created:
        assert employee.company == company


@pytest.mark.asyncio
async def test_insert_many_empty_list(create_base_and_connect):

    created = await Employee.insert_many([])

    assert created == []
