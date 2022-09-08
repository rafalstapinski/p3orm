from __future__ import annotations

import pytest

from test.fixtures.tables import Company, Employee
from test.sqlite.fixtures.fixtures import create_base_and_connect


@pytest.mark.asyncio
async def test_update_one(create_base_and_connect):

    fetched = await Company.fetch_one(Company.id == 1)

    fetched.name = "Company Name Changed"

    updated = await Company.update_one(fetched)

    assert updated == fetched
    assert updated.name == "Company Name Changed"

    fetched.name = "name changed locally without commiting to database"

    assert updated != fetched


@pytest.mark.asyncio
async def test_update_one_prefetch(create_base_and_connect):

    employee = await Employee.fetch_one(Employee.id == 1)

    company_one = await Company.fetch_one(Company.id == 1)
    company_two = await Company.fetch_one(Company.id == 2)

    assert employee.company_id == company_one.id

    employee.company_id = company_two.id

    employee = await Employee.update_one(employee, prefetch=[[Employee.company]])

    assert employee.company == company_two
