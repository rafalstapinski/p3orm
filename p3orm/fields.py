from __future__ import annotations

from enum import Enum
from typing import Any, Type

import pypika

from p3orm.exceptions import P3ormException

# from p3orm.table import Table
#
# T = TypeVar("T", bound=Table)


#
class FieldMeta(type):
    ...


#     def __getattribute__(cls: Type[PormField], __name: str) -> Any:
#         return getattr(cls._pypika_field, __name)


class PormField:
    pk: bool
    db_gen: bool
    db_default: bool
    column_name: str

    _field_name: str
    _data_type: Type
    _pypika_field: pypika.Field

    def __init__(self, pk: bool, db_gen: bool, db_default: bool, column_name: str | None):
        self.pk = pk
        self.db_gen = db_gen
        self.db_default = db_default
        if column_name:
            self.column_name = column_name


#
# class PK(PormField):
#     pk = True
#
#
# class DBGen(PormField):
#     db_gen = True
#
#
# class DBDefault(PormField):
#     db_default = True
#


class RelationshipType(str, Enum):
    foreign_key = "foreign_key"
    reverse = "reverse"


class PormRelationship[T]:
    self_column: str
    foreign_column: str
    relationship_type: RelationshipType

    _data_type: Type[T]
    _field_name: str

    def __init__(self, self_column: str, foreign_column: str, relationship_type: RelationshipType) -> None:
        self.self_column = self_column
        self.foreign_column = foreign_column
        self.relationship_type = relationship_type


def Column(pk: bool = False, db_gen: bool = False, has_default: bool = False, column_name: str | None = None) -> Any:
    if has_default:
        raise NotImplementedError("has_default not implemented yet")

    return PormField(
        pk=pk,
        db_gen=db_gen,
        db_default=has_default,
        column_name=column_name,
    )


def f(x: Any) -> pypika.Field:
    if not isinstance(x, PormField):
        raise P3ormException(f"Expected PormField, got {type(x)}")
    return x._pypika_field


def ForeignKeyRelationship(self_column: str, foreign_column: str) -> Any:
    return PormRelationship(self_column, foreign_column, RelationshipType.foreign_key)


def ReverseRelationship(self_column: str, foreign_column: str) -> Any:
    return PormRelationship(self_column, foreign_column, RelationshipType.reverse)
