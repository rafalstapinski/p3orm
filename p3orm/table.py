from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar, Type

import attrs
from pydantic import BaseModel, ConfigDict
from pypika import Criterion
from pypika import Field as PyPikaField
from pypika.queries import QueryBuilder

from p3orm.exceptions import MissingTablename, SinglePrimaryKeyException
from p3orm.utils import is_optional, parameterize


class TableMemo:
    fields: dict[str, _PormField]
    columns: dict[str, _PormField]
    relationships: dict[str, _PormRelationship]
    factory: Type


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
        if is_optional(self.data_type):
            type = self.data_type
        else:
            type = self.data_type.__name__

        return f"<UNLOADED RELATIONSHIP {name=} {type=}>"


@dataclass
class DB_GENERATED[T]:
    name: str
    column: str
    data_type: Type[T]

    def __repr__(self) -> str:
        name = self.name
        column = self.column
        if is_optional(self.data_type):
            type = self.data_type
        else:
            type = self.data_type.__name__

        return f"<DB WILL SET VALUE {name=} {column=} {type=}>"


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

        # prepare all the criterion so they all know which table they belong to

    def __new__(cls, /, **create_fields: dict[str, Any]):
        if not (memo := TABLES.get(cls)):
            memo = cls._init_stuff()

        obj = memo.factory(**create_fields)
        for field_name, field in memo.fields.items():
            if field.db_gen:
                setattr(
                    obj,
                    field_name,
                    DB_GENERATED[field._data_type](
                        name=field_name,
                        column=field.column_name,
                        data_type=field._data_type,
                    ),
                )

        for field_name, relationship in memo.relationships.items():
            setattr(
                obj,
                field_name,
                UNLOADED_RELATIONSIP[relationship._data_type](
                    name=field_name,
                    data_type=relationship._data_type,
                ),
            )

        return obj

    @classmethod
    def _init_stuff(cls) -> TableMemo:
        memo = TableMemo()
        memo.fields = {}
        memo.relationships = {}
        memo.columns = {}
        type_hints = typing.get_type_hints(cls)

        # tack on fields and relationships
        for table in cls.__mro__:
            for field_name in table.__dict__:
                if isinstance(field := getattr(table, field_name), _PormField):
                    field._field_name = field_name
                    field._data_type = type_hints[field_name]

                    if not hasattr(field, "column_name"):
                        field.column_name = field_name

                    memo.fields[field_name] = field
                    memo.columns[field.column_name] = field

                elif isinstance(relationship := getattr(cls, field_name), _PormRelationship):
                    relationship._data_type = type_hints[field_name]
                    memo.relationships[field_name] = relationship

        if len([f for f in memo.fields.values() if f.pk]) != 1:
            raise SinglePrimaryKeyException(f"{cls.__name__} must has 1 primary")

        # tack on the model factory
        factory_fields: dict[str, attrs.Attribute] = {}
        for field_name, field in memo.fields.items():
            field_kwargs = {}
            field_kwargs["type"] = field._data_type

            if field.db_default or field.db_gen:
                field_kwargs["default"] = DB_GENERATED[field._data_type](
                    name=field_name, column=field.column_name, data_type=field._data_type
                )
            elif is_optional(field._data_type):
                field_kwargs["default"] = None

            factory_fields[field_name] = attrs.field(**field_kwargs)

        for field_name, relationship in memo.relationships.items():
            factory_fields[field_name] = attrs.field(
                type=relationship._data_type,
                default=UNLOADED_RELATIONSIP[relationship._data_type](
                    name=field_name, data_type=relationship._data_type
                ),
            )

        memo.factory = attrs.make_class(
            name=cls.__name__,
            attrs=factory_fields,
            kw_only=True,
            slots=True,
        )

        TABLES[cls] = memo
        return memo

    @classmethod
    def from_(cls) -> QueryBuilder:
        return querybuilder().from_(cls.__tablename__)

    @classmethod
    async def fetch_one[T](cls: Type[T], /, criterion: Criterion) -> T:
        parameterized_criterion, query_args = parameterize(criterion)

        query: QueryBuilder = cls.select().where(parameterized_criterion)


class _PormField[T]:
    pk: bool
    db_gen: bool
    db_default: bool
    column_name: str

    _field_name: str
    _data_type: Type[T]
    _pypika_field: PyPikaField

    def __init__(self, pk: bool, db_gen: bool, db_default: bool, column_name: str | None) -> None:
        self.pk = pk
        self.db_gen = db_gen
        self.db_default = db_default
        if column_name:
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


def Column(pk: bool = False, db_gen: bool = False, has_default: bool = False, column_name: str | None = None) -> Any:
    return _PormField(
        pk=pk,
        db_gen=db_gen,
        db_default=has_default,
        column_name=column_name,
    )


def ForeignKeyRelationship(self_column: str, foreign_column: str) -> Any:
    return _PormRelationship(self_column, foreign_column, RelationshipType.foreign_key)


def ReverseRelationship(self_column: str, foreign_column: str) -> Any:
    return _PormRelationship(self_column, foreign_column, RelationshipType.reverse)
