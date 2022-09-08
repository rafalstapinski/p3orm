import pytest
from pydantic import ValidationError

from p3orm import Column, Table
from p3orm.exceptions import MissingTablename

from test.fixtures.tables import Company
from test.sqlite.fixtures.fixtures import create_base_and_connect


def test_table_has_tablename():

    with pytest.raises(MissingTablename):

        class MyTable(Table):
            id = Column(int, "id", pk=True, autogen=True)


@pytest.mark.asyncio
async def test_table_different_field_from_column(create_base_and_connect):

    company = await Company.fetch_one(Company.id == 1)
    assert company.some_property == "yeet"

    company = await Company.fetch_one(Company.id == 2)
    assert company.some_property == None

    company = await Company.fetch_one(Company.some_property == "yeet")
    assert company.some_property == "yeet"
    assert company.id == 1


@pytest.mark.asyncio
async def test_table_fails_on_required_property(create_base_and_connect):
    class _Company(Table):
        __tablename__ = "company"
        id = Column(int, pk=True, autogen=True)
        column_name = Column(str)

    with pytest.raises(KeyError):
        await _Company.fetch_one(_Company.id == 2)

    with pytest.raises(ValidationError):
        _Company(id=1)


def test_meta_table_no_tablename():
    class MyMetaTable(Table):
        class Meta:
            meta_table = True

        id = Column(int, "id", pk=True, autogen=True)


def test_table_can_have_pk_on_parent():
    class Entity(Table):
        class Meta:
            meta_table = True

        id = Column(int, "id", pk=True, autogen=True)

    class MyTable(Entity):
        __tablename__ = "my_table"
