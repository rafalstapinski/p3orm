from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from test.fixtures.helpers import create_base_and_connect
from test.fixtures.tables import Company, Employee

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_fetch_related_foreign_key(postgresql: connection):

    await create_base_and_connect(postgresql)
    employee = await Employee.fetch_one(Employee.id == 1)
    await Employee.fetch_related([employee], ((Employee.company,),))

    company = await Company.fetch_one(Company.id == employee.company_id)

    assert employee.company == company


@pytest.mark.asyncio
async def test_fetch_related_reverse_relation(postgresql: connection):

    await create_base_and_connect(postgresql)
    company = await Company.fetch_one(Company.id == 1)
    await Company.fetch_related([company], ((Company.employees,),))

    employees = await Employee.fetch_all(Employee.company_id == company.id)

    assert sorted(company.employees, key=lambda e: e.id) == sorted(employees, key=lambda e: e.id)
