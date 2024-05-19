from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, Type, TypeVar

from pypika.terms import Criterion as PyPikaCriterion
from pypika.terms import Field as PyPikaField
from pypika.terms import Parameter

from p3orm.exceptions import P3ormException

if TYPE_CHECKING:
    from p3orm.table import Table


T = TypeVar("T", bound="Table")


class _DEFAULT(Parameter):
    def __init__(self) -> None:
        super().__init__("DEFAULT")


DEFAULT = _DEFAULT()


class PormField:
    pk: bool
    db_gen: bool
    db_default: bool
    column_name: str

    _field_name: str
    _data_type: Type[Any]
    _pypika_field: PyPikaField

    def __init__(self, pk: bool, db_gen: bool, db_default: bool, column_name: str | None):
        self.pk = pk
        self.db_gen = db_gen
        self.db_default = db_default
        if column_name:
            self.column_name = column_name


class RelationshipType(str, Enum):
    foreign_key = "foreign_key"
    reverse = "reverse"
    reverse_one = "reverse_one"


class PormRelationship(Generic[T]):
    self_column: str
    foreign_column: str
    relationship_type: RelationshipType
    criterion: PyPikaCriterion | None

    _data_type: Type[T]
    _field_name: str

    def __init__(
        self,
        self_column: str,
        foreign_column: str,
        relationship_type: RelationshipType,
        criterion: PyPikaCriterion | None,
    ) -> None:
        self.self_column = self_column
        self.foreign_column = foreign_column
        self.relationship_type = relationship_type
        self.criterion = criterion

    def is_plural(self) -> bool:
        return self.relationship_type == RelationshipType.reverse


def Column(pk: bool = False, db_gen: bool = False, has_default: bool = False, column_name: str | None = None) -> Any:
    if has_default:
        raise NotImplementedError("has_default not implemented yet")

    return PormField(
        pk=pk,
        db_gen=db_gen,
        db_default=has_default,
        column_name=column_name,
    )


def f(x: Any) -> PyPikaField:
    if not isinstance(x, PormField):
        raise P3ormException(f"Expected PormField, got {type(x)}")
    return x._pypika_field


def ForeignKeyRelationship(self_column: str, foreign_column: str, criterion: PyPikaCriterion | None = None) -> Any:
    return PormRelationship(self_column, foreign_column, RelationshipType.foreign_key, criterion)


def ReverseRelationship(self_column: str, foreign_column: str, criterion: PyPikaCriterion | None = None) -> Any:
    return PormRelationship(self_column, foreign_column, RelationshipType.reverse, criterion)


def ReverseOneToOneRelationship(self_column: str, foreign_column: str, criterion: PyPikaCriterion | None = None) -> Any:
    return PormRelationship(self_column, foreign_column, RelationshipType.reverse_one, criterion)
