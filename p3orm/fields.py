from __future__ import annotations

from enum import Enum
from typing import NoReturn, Optional, Type, Union

from pypika import Field

from p3orm.exceptions import UnloadedRelationship
from p3orm.types import T


class UNLOADED:
    def __getattribute__(self, name) -> NoReturn:
        if name == "__class__":
            return UNLOADED

        raise UnloadedRelationship("_Relationship has not yet been loaded from the database")

    def __getitem__(*args) -> NoReturn:
        raise UnloadedRelationship("_Relationship has not yet been loaded from the database")

    def __eq__(self, other):
        return isinstance(other, UNLOADED)

    def __repr__(self) -> str:
        return f"<UNLOADED RELATIONSHIP>"


class _PormField(Field):
    pk: bool
    autogen: bool
    _type: Type
    field_name: str

    def __init__(
        self,
        _type: Type,
        column_name: Optional[str] = None,
        pk: Optional[bool] = False,
        autogen: Optional[bool] = False,
    ):
        self._type = _type
        self.column_name = column_name
        self.pk = pk
        self.autogen = autogen

        # This is used by underlying pypika logic, but column_name is used in p3orm for sanity
        self.name = column_name


def Column(
    _type: Type[T],
    column_name: Optional[str] = None,
    *,
    pk: Optional[bool] = False,
    autogen: Optional[bool] = False,
) -> Union[T, _PormField]:
    return _PormField(
        _type=_type,
        column_name=column_name,
        pk=pk,
        autogen=autogen,
    )


class RelationshipType(str, Enum):
    foreign_key = "foreign_key"
    reverse = "reverse"


class _Relationship:

    self_column: str
    foreign_column: str
    relationship_type: RelationshipType

    def __init__(self, self_column: str, foreign_column: str, relationship_type: RelationshipType):
        self.self_column = self_column
        self.foreign_column = foreign_column
        self.relationship_type = relationship_type


def ForeignKeyRelationship(self_column: str, foreign_column: str) -> _Relationship:
    return _Relationship(self_column, foreign_column, RelationshipType.foreign_key)


def ReverseRelationship(self_column: str, foreign_column: str) -> _Relationship:
    return _Relationship(self_column, foreign_column, RelationshipType.reverse)
