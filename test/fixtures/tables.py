from datetime import datetime

from p3orm.table import Column, Table


class Company(Table):

    __tablename__ = "company"

    id = Column(int, "id", pk=True, autogen=True)
    name = Column(str, "name")
    created_at = Column(datetime, "created_at", autogen=True)


class Employee(Table):

    __tablename__ = "employee"

    id = Column(int, "id", pk=True, autogen=True)
    name = Column(str, "name")
    company_id = Column(int, "company_id")
    created_at = Column(datetime, "created_at", autogen=True)


class OrgChart(Table):

    __tablename__ = "org_chart"

    id = Column(int, "id", pk=True, autogen=True)
    manager_id = Column(int, "manager_id")
    report_id = Column(int, "report_id")
