from __future__ import annotations

from typing import Type

from attrs import make_class

from p3orm.exceptions import MissingTablename


class Table:
    __tablename__: str
    __meta__: bool = False

    def __init_subclass__(cls) -> None:
        if cls.__meta__:
            return

        if not cls.__tablename__:
            raise MissingTablename(f"{cls} is missing a __tablename__ property")

    #
    # Introspective methods
    #
    @classmethod
    def _fields(cls) -> list[_PormField]:
        fields: list[_PormField] = []
        for table in cls.__mro__:
            for field_name in table.__dict__:
                if isinstance(field := getattr(table, field_name), _PormField):
                    # if field.c
                    ...

        return fields


class _PormField[T]:
    pypika_field: ...
    attr_field: ...

    data_type: Type[T]
    pk: bool
    dbgen: bool
    column_name: str | None

    def __init__(self, data_type: Type[T], pk: bool, dbgen: bool, column_name: str | None) -> None:
        self.data_type = data_type
        self.pk = pk
        self.dbgen = dbgen
        self.column_name = column_name


def Column[T](data_type: Type[T], pk: bool = False, dbgen: bool = False, column_name: str | None = None) -> T:
    return _PormField[data_type](
        data_type=data_type,
        pk=pk,
        dbgen=dbgen,
        column_name=column_name,
    )


#
# class Column[T]:
#     def __init__(self, *, pk: bool = False, dbgen: bool = False) -> None:
#         ...
#
#
# class ForeignKeyRelationship[T]:
#     def __init__(self, *, self_column: str, foreign_column: str) -> None:
#         ...
#
#
# class ReverseRelationship[T]:
#     def __init__(self, *, self_column: str, foreign_column: str) -> None:
#         ...
