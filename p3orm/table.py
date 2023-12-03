from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Type,
    cast,
    dataclass_transform,
    get_args,
    get_origin,
    overload,
)

import attrs
import pypika
from attrs import make_class
from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from pydantic import create_model

from p3orm.exceptions import MissingTablename, SinglePrimaryKeyException
from p3orm.utils import is_optional


class TableMemo:
    fields: dict[str, _PormField] = {}
    columns: dict[str, _PormField] = {}
    relationships: dict[str, _PormRelationship] = {}
    factory: Callable


TABLES: dict[Type[Table], TableMemo] = {}


class TableInstance(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        frozen=False,
    )

    __pydantic_complete__ = False

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BaseModel):
            return (
                self.__dict__ == other.__dict__
                and self.__pydatic_private__ == other.__pydantic_private__  # type: ignore
                and self.__pydantic_extra__ == other.__pydantic_extra__
            )
        return NotImplemented


@dataclass
class UNLOADED_RELATIONSIP[T]:
    name: str
    data_type: Type[T]

    def __repr__(self) -> str:
        name = self.name
        data_type = self.data_type
        return f"<UNLOADED RELATIONSHIP {name=} {data_type=}>"


@typing.dataclass_transform()
class TableMeta(type):
    ...


class Table(metaclass=TableMeta):
    __tablename__: ClassVar[str]
    __meta__: ClassVar[bool] = False

    def __init_subclass__(cls) -> None:
        if cls.__meta__:
            return

        if not cls.__tablename__:
            raise MissingTablename(f"{cls} is missing a __tablename__ property")

        # gen TableMemo
        memo = TableMemo()
        memo.fields = {}
        type_hints = typing.get_type_hints(cls)

        # tack on fields and relationships
        for table in cls.__mro__:
            for field_name in table.__dict__:
                if isinstance(field := getattr(table, field_name), _PormField):
                    field._field_name = field_name
                    field._data_type = type_hints[field_name]

                    if not field.column_name:
                        field.column_name = field_name

                    memo.fields[field_name] = field
                    memo.columns[field.column_name] = field

                elif isinstance(relationship := getattr(cls, field_name), _PormRelationship):
                    relationship._data_type = type_hints[field_name]
                    memo.relationships[field_name] = relationship

        if len([f for f in memo.fields.values() if f.pk]) != 1:
            raise SinglePrimaryKeyException(f"{cls.__name__} must has 1 primary")

        # tack on the model factory
        factory_model_kwargs = {}
        for field_name, field in memo.fields.items():
            default = ...
            if field.dbgen or is_optional(field._data_type):
                default = None

            factory_model_kwargs[field_name] = (field._data_type, PydanticField(default=default))

        for field_name, relationship in memo.relationships.items():
            factory_model_kwargs[field_name] = (
                relationship._data_type,
                PydanticField(
                    default=UNLOADED_RELATIONSIP[relationship._data_type](
                        name=field_name, data_type=relationship._data_type
                    )
                ),
            )

        class _TableInstance(TableInstance):
            ...

        memo.factory = create_model(cls.__name__, __base__=_TableInstance, **factory_model_kwargs)

        TABLES[cls] = memo


class _PormField[T]:
    pk: bool
    dbgen: bool
    column_name: str | None

    _field_name: str
    _data_type: Type[T]
    _pypika_field: pypika.Field

    def __init__(self, pk: bool, dbgen: bool, column_name: str | None) -> None:
        self.pk = pk
        self.dbgen = dbgen
        self.column_name = column_name


class RelationshipType(str, Enum):
    foreign_key = "foreign_key"
    reverse = "reverse"


class _PormRelationship[T]:
    self_column: str
    foreign_column: str
    relationship_type: RelationshipType

    _data_type: Type[T]

    def __init__(self, self_column: str, foreign_column: str, relationsip_type: RelationshipType) -> None:
        self.self_column = self_column
        self.foreign_column = foreign_column
        self.relationship_type = relationsip_type


def Column(pk: bool = False, dbgen: bool = False, column_name: str | None = None) -> Any:
    return _PormField(
        pk=pk,
        dbgen=dbgen,
        column_name=column_name,
    )


def ForeignKeyRelationship(self_column: str, foreign_column: str):
    return _PormRelationship(self_column, foreign_column, RelationshipType.foreign_key)


def ReverseRelationship(self_column: str, foreign_column: str):
    return _PormRelationship(self_column, foreign_column, RelationshipType.reverse)
