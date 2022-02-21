from __future__ import annotations

from datetime import datetime

from p3orm.table import Column, ForeignKeyRelationship, ReverseRelationship, Table


class Company(Table):

    __tablename__ = "company"

    id = Column(int, "id", pk=True, autogen=True)
    name = Column(str, "name")
    created_at = Column(datetime, "created_at", autogen=True)

    employees: list[Employee] = ReverseRelationship(self_field="id", other_field="company_id")


class Employee(Table):

    __tablename__ = "employee"

    id = Column(int, "id", pk=True, autogen=True)
    name = Column(str, "name")
    company_id = Column(int, "company_id")
    created_at = Column(datetime, "created_at", autogen=True)

    company: Company = ForeignKeyRelationship(self_field="company_id", other_field="id")


class OrgChart(Table):

    __tablename__ = "org_chart"

    id = Column(int, "id", pk=True, autogen=True)
    manager_id = Column(int, "manager_id")
    report_id = Column(int, "report_id")
