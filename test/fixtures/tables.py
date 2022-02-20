from datetime import datetime

from p3orm.table import PormField, Table


class Company(Table):

    __tablename__ = "company"

    id: int = PormField("id", pk=True, autogen=True)
    name: str = PormField("name")
    created_at: datetime = PormField("created_at")


class Employee(Table):

    __tablename__ = "employee"

    id: int = PormField("id", pk=True, autogen=True)
    name: str = PormField("name")
    company_id: int = PormField("company_id")
    created_at: datetime = PormField("created_at")


class OrgChart(Table):

    __tablename__ = "org_chart"

    id: int = PormField("id", pk=True, autogen=True)
    manager_id: int = PormField("manager_id")
    report_id: int = PormField("report_id")
