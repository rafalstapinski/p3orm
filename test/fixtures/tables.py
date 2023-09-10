from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from p3orm import Column, ForeignKeyRelationship, ReverseRelationship, Table


class Company(Table):
    __tablename__ = "company"

    id = Column(int, pk=True, autogen=True)
    name = Column(str)
    created_at = Column(datetime, autogen=True)
    some_property = Column(Optional[str], "column_name")

    employees: List[Employee] = ReverseRelationship(self_column="id", foreign_column="company_id")


class Employee(Table):
    __tablename__ = "employee"

    id = Column(int, pk=True, autogen=True)
    name = Column(str)
    company_id = Column(Optional[int])
    created_at = Column(datetime, autogen=True)

    company: Company = ForeignKeyRelationship(self_column="company_id", foreign_column="id")


class OrgChart(Table):
    __tablename__ = "org_chart"

    id = Column(int, pk=True, autogen=True)
    manager_id = Column(int)
    report_id = Column(int)

    manager: Employee = ForeignKeyRelationship(self_column="manager_id", foreign_column="id")
    report: Employee = ForeignKeyRelationship(self_column="report_id", foreign_column="id")
