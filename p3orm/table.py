from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Type

import attrs
import pypika
from pypika.dialects import PostgreSQLQueryBuilder

from p3orm.exceptions import MissingTablename, P3ormException, SinglePrimaryKeyException
from p3orm.fields import PormField, PormRelationship
from p3orm.utils import is_optional

if TYPE_CHECKING:
    from p3orm.drivers.base import Driver


class TableMemo:
    table: Type[Table]
    fields: dict[str, PormField]
    columns: dict[str, PormField]
    relationships: dict[PormRelationship, str]
    factory: Type
    record_t_kwarg_map: dict[str, str]
    record_kwarg_map: dict[str, str]
    driver: Driver


TABLES: dict[Type[Table], TableMemo] = {}


def querybuilder():
    return PostgreSQLQueryBuilder()


@dataclass
class UNLOADED_RELATIONSIP[T]:
    name: str
    data_type: Type[T]

    def __repr__(self) -> str:
        name = self.name
        # if is_optional(self.data_type):
        #     type = self.data_type
        # else:
        #     type = self.data_type.__name__
        type = self.data_type

        return f"<UNLOADED RELATIONSHIP {name=} {type=}>"


@dataclass
class DB_GENERATED[T]:
    name: str
    column: str
    data_type: Type[T]

    def __repr__(self) -> str:
        name = self.name
        column = self.column
        # if is_optional(self.data_type):
        #     type = self.data_type
        # else:
        #     type = self.data_type.__name__
        type = self.data_type

        return f"<DB WILL SET VALUE {name=} {column=} {type=}>"


@typing.dataclass_transform()
class TableMeta(type):
    def from_(cls: Type[Table]) -> PostgreSQLQueryBuilder:
        print(f"{cls=} {type(cls)=}")
        return querybuilder().from_(cls.__tablename__)

    def select(cls: Type[Table]) -> PostgreSQLQueryBuilder:
        return cls.from_().select("*")

    def delete(cls: Type[Table]) -> PostgreSQLQueryBuilder:
        return querybuilder().delete().from_(cls.__tablename__)

    def update(cls: Type[Table]) -> PostgreSQLQueryBuilder:
        return querybuilder().update(cls.__tablename__)


class Table(metaclass=TableMeta):
    __tablename__: ClassVar[str]
    __meta__: ClassVar[bool] = False

    __memo__: ClassVar[TableMemo]

    # @classmethod
    # async def fetch_one[T](cls: Type[T | Self], /, criterion: Criterion) -> T:
    #     parameterized_criterion, query_args = parameterize(criterion)
    #
    #     query: QueryBuilder = cls.select().where(parameterized_criterion)
    #     query = query.limit(2)
    #
    def __new__(cls, /, **create_fields: dict[str, Any]):
        if not (hasattr(cls, "__memo__") and (memo := cls.__memo__)):
            raise P3ormException(f"table {cls} not initalized")

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

        for relationship, field_name in memo.relationships.items():
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
    def _init_stuff(cls, driver: Driver) -> TableMemo:
        memo = TableMemo()
        memo.table = cls
        memo.driver = driver
        memo.fields = {}
        memo.relationships = {}
        memo.columns = {}
        memo.record_t_kwarg_map = {}
        memo.record_kwarg_map = {}

        type_hints = typing.get_type_hints(cls)

        # tack on fields and relationships
        for table in cls.__mro__:
            for field_name in table.__dict__:
                if isinstance(field := getattr(table, field_name), PormField):
                    field._field_name = field_name
                    field._data_type = type_hints[field_name]

                    if not hasattr(field, "column_name"):
                        field.column_name = field_name

                    field._pypika_field = pypika.Field(
                        name=field.column_name,
                        table=pypika.Table(cls.__tablename__),
                    )

                    memo.fields[field_name] = field
                    memo.columns[field.column_name] = field
                    memo.record_kwarg_map[field.column_name] = field_name
                    memo.record_t_kwarg_map[f"{cls.__tablename__}.{field.column_name}"] = field_name

                elif isinstance(relationship := getattr(cls, field_name), PormRelationship):
                    relationship._data_type = type_hints[field_name]
                    memo.relationships[relationship] = field_name

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

        for relationship, field_name in memo.relationships.items():
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
        cls.__memo__ = memo
        print(f"SETTING {cls=} {cls.__memo__=}")
        return memo

    def __init_subclass__(cls) -> None:
        if cls.__meta__:
            return

        if not cls.__tablename__:
            raise MissingTablename(f"{cls} is missing a __tablename__ property")

            # prepare all the criterion so they all know which table they belong to

            # for field in fields:
            ...
