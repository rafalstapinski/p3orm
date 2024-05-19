from __future__ import annotations

import dataclasses
import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generator, Generic, Type, TypeVar, get_args

from pypika.dialects import PostgreSQLQueryBuilder
from pypika.terms import Field as PyPikaField

from p3orm.exceptions import (
    MisingPrimaryKeyException,
    MissingTablename,
    P3ormException,
    UnloadedRelationshipException,
)
from p3orm.fields import PormField, PormRelationship, RelationshipType
from p3orm.utils import is_optional

if TYPE_CHECKING:
    from p3orm import Driver

T = TypeVar("T", bound="Table")


class TableMemo:
    table: Type[Table]
    pk: list[PormField]
    fields: dict[str, PormField]
    columns: dict[str, PormField]
    relationships: dict[str, PormRelationship[Any]]
    factory: Type[Any]
    record_t_kwarg_map: dict[str, str]
    record_kwarg_map: dict[str, str]
    driver: Driver


TABLES: dict[Type[Table], TableMemo] = {}


def querybuilder() -> PostgreSQLQueryBuilder:
    return PostgreSQLQueryBuilder()


@dataclass
class UNLOADED_RELATIONSHIP(Generic[T]):
    name: str
    data_type: Type[T]

    def __get__(self, _: Table, owner: Type[Table]):
        raise UnloadedRelationshipException(f"<{owner}> relationship {self.name=} not loaded")

    def __repr__(self) -> str:
        name = self.name
        type = self.data_type

        return f"<UNLOADED RELATIONSHIP {name=} {type=}>"

    def __bool__(self) -> bool:
        return False


@dataclass
class DB_GENERATED(Generic[T]):
    name: str
    column: str
    data_type: Type[T]

    def __repr__(self) -> str:
        table = self.name
        column = self.column
        type = self.data_type

        return f"<DB WILL SET VALUE {table=} {column=} {type=}>"


@typing.dataclass_transform()
class TableMeta(type):
    def from_(cls: Type[Table]) -> PostgreSQLQueryBuilder:  # type: ignore
        return querybuilder().from_(cls.__tablename__)

    def select(cls: Type[Table], what: Any = None) -> PostgreSQLQueryBuilder:  # type: ignore
        return cls.from_().select(what or "*")

    def delete(cls: Type[Table]) -> PostgreSQLQueryBuilder:  # type: ignore
        return querybuilder().delete().from_(cls.__tablename__)

    def update(cls: Type[Table]) -> PostgreSQLQueryBuilder:  # type: ignore
        return querybuilder().update(cls.__tablename__)


# we need to check instead of checking directly because a __meta__ = True class
# will pass that down to all children. so we determine if __meta__ is set on the
# class itself, not on any parents, and then use that to determine
# tl;dr table is meta if that class, and that class specifically, has __meta__ set to True
def _is_meta_table(cls: Type[Table]) -> bool:
    if hasattr(cls, "__meta__"):
        if "__meta__" in cls.__dict__:
            return cls.__dict__["__meta__"]

    return False


def create_dataclass(
    class_name: str,
    fields: list[str | tuple[str, type] | tuple[str, type, dataclasses.Field]],
) -> type:
    return dataclasses.make_dataclass(
        class_name,
        fields,
        slots=True,
        match_args=True,
        kw_only=True,
    )


"""
def create_factory(
    class_name: str,
    fields: list[str | tuple[str, type] | tuple[str, type, Any]],
):
    def __init__(self, **kwargs):
        init_kwargs = {}
        for field in fields:
            match field:
                case str(field_name):
                    ...
                case (field_name, field_type):
                    ...
                case (field_name, field_type, field_default):
                    ...
"""


class Table(metaclass=TableMeta):
    __tablename__: ClassVar[str]
    __meta__: ClassVar[bool] = False

    __memo__: ClassVar[TableMemo]

    def __new__(cls, /, **create_fields: dict[str, Any]):  # type: ignore
        # TODO: cython? teehee
        if not (hasattr(cls, "__memo__") and (memo := cls.__memo__)):
            raise P3ormException(f"table {cls} not initalized")

        return memo.factory(**create_fields)

    @classmethod
    def __validate(cls, v: Table | Any, _) -> Table:
        assert cls.__name__ == v.__class__.__name__, f"must be a valid {cls.__name__}"
        return v

    @classmethod
    def __get_validators__(cls) -> Generator[Callable, None, None]:
        yield cls.__validate

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
        memo.pk = []

        type_hints = typing.get_type_hints(cls)

        # tack on fields and relationships
        for table in cls.__mro__:
            for field_name in table.__dict__:
                if isinstance(field := getattr(table, field_name), PormField):
                    field._field_name = field_name
                    field._data_type = type_hints[field_name]

                    if not hasattr(field, "column_name"):
                        field.column_name = field_name

                    field._pypika_field = PyPikaField(name=field.column_name)

                    memo.fields[field_name] = field
                    memo.columns[field.column_name] = field
                    memo.record_kwarg_map[field.column_name] = field_name
                    memo.record_t_kwarg_map[f"{cls.__tablename__}.{field.column_name}"] = field_name

                    if field.pk:
                        memo.pk.append(field)

                elif isinstance(relationship := getattr(cls, field_name), PormRelationship):
                    if relationship.relationship_type in (RelationshipType.foreign_key, RelationshipType.reverse_one):
                        relationship._data_type = type_hints[field_name]
                    else:
                        relationship._data_type = get_args(type_hints[field_name])[0]

                    relationship._field_name = field_name
                    memo.relationships[field_name] = relationship

        if len(memo.pk) == 0:
            raise MisingPrimaryKeyException(f"{cls.__name__} must have at least 1 column to uniquely identify rows")

        # tack on the model factory
        factory_fields: list[str | tuple[str, type] | tuple[str, type, dataclasses.Field]] = []
        for field_name, field in memo.fields.items():
            field_opts = [field_name, field._data_type]

            if field.db_default or field.db_gen:
                field_opts.append(
                    dataclasses.field(
                        default_factory=lambda: DB_GENERATED[field._data_type](
                            name=field_name, column=field.column_name, data_type=field._data_type
                        )
                    )
                )
            elif is_optional(field._data_type):
                field_opts.append(dataclasses.field(default=None))

            factory_fields.append(tuple(field_opts))

        for field_name, relationship in memo.relationships.items():
            factory_fields.append(
                (
                    field_name,
                    relationship._data_type,
                    dataclasses.field(
                        default_factory=lambda: UNLOADED_RELATIONSHIP[relationship._data_type](  # type: ignore -> typeshed says this returns T, but it returns Field[T]
                            name=field_name, data_type=relationship._data_type
                        )
                    ),
                )
            )

        memo.factory = create_dataclass(cls.__name__, factory_fields)

        TABLES[cls] = memo
        cls.__memo__ = memo
        return memo

    def __init_subclass__(cls) -> None:
        if _is_meta_table(cls):
            return

        if not cls.__tablename__:
            raise MissingTablename(f"{cls} is missing a __tablename__ property")
