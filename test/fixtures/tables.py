from __future__ import annotations

from datetime import datetime
from typing import List

from p3orm import Column, ForeignKeyRelationship, ReverseRelationship, Table


class Company(Table):

    __tablename__ = "company"

    id = Column(int, pk=True, autogen=True)
    name = Column(str)
    time_created = Column(datetime, "created_at", autogen=True)

    employees: List[Employee] = ReverseRelationship(self_column="id", foreign_column="company_id")


class Employee(Table):

    __tablename__ = "employee"

    id = Column(int, pk=True, autogen=True)
    name = Column(str)
    company_id = Column(int, "company_id")
    created_at = Column(datetime, "created_at", autogen=True)

    company: Company = ForeignKeyRelationship(self_column="company_id", foreign_column="id")


class OrgChart(Table):

    __tablename__ = "org_chart"

    id = Column(int, "id", pk=True, autogen=True)
    manager_id = Column(int, "manager_id")
    report_id = Column(int, "report_id")

    manager: Employee = ForeignKeyRelationship(self_column="manager_id", foreign_column="id")
    report: Employee = ForeignKeyRelationship(self_column="report_id", foreign_column="id")
