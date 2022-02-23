from __future__ import annotations

import pytest

from test.fixtures.helpers import create_base_and_connect
from test.fixtures.tables import Company, Employee


@pytest.mark.asyncio
async def test_fetch_related_foreign_key(create_base_and_connect):

    employee = await Employee.fetch_one(Employee.id == 1)
    [employee_with_company] = await Employee.fetch_related([employee], [[Employee.company]])

    company = await Company.fetch_one(Company.id == employee_with_company.company_id)

    assert employee_with_company.company == company


@pytest.mark.asyncio
async def test_fetch_related_reverse_relation(create_base_and_connect):

    company = await Company.fetch_one(Company.id == 1)
    [company_with_employees] = await Company.fetch_related([company], [[Company.employees]])

    employees = await Employee.fetch_all(Employee.company_id == company.id)

    assert sorted(company_with_employees.employees, key=lambda e: e.id) == sorted(employees, key=lambda e: e.id)


@pytest.mark.asyncio
async def test_fetch_related_clears_unloaded_relationships(create_base_and_connect):

    company = await Company.fetch_one(Company.id == 2)
    [company_without_employees] = await Company.fetch_related([company], [[Company.employees]])

    assert company_without_employees.employees == []

    employee = await Employee.fetch_one(Employee.id == 6)
    [employee_without_company] = await Employee.fetch_related([employee], [[Employee.company]])

    assert employee_without_company.company == None
