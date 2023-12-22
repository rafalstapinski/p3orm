from __future__ import annotations

import abc
from typing import Any, Generic, Type, TypeVar

import asyncpg
import pypika
from pypika.dialects import PostgreSQLQuery, PostgreSQLQueryBuilder
from pypika.queries import QueryBuilder
from pypika.terms import Criterion, Parameter

from p3orm.drivers.base import Driver
from p3orm.exceptions import P3ormException
from p3orm.fields import PormField
from p3orm.table import DB_GENERATED, Table
from p3orm.utils import parameterize

T = TypeVar("T", bound=Table)


class Postgres(Driver):
    connection: asyncpg.Connection | None = None
    pool: asyncpg.Pool | None = None

    async def connect(
        self,
        dsn: str | None = None,
        *,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        host: str | None = None,
        port: int | None = None,
        **asyncpg_kwargs: dict[Any, Any],
    ):
        if self.is_connected():
            raise P3ormException("already connected")

        self.pool = None
        self.connection = await asyncpg.connect(
            dsn=dsn,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            **asyncpg_kwargs,  # type: ignore
        )

    async def connect_pool(
        self,
        dsn: str | None = None,
        *,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        host: str | None = None,
        port: int | None = None,
        **asyncpg_kwargs: dict[Any, Any],
    ):
        if self.is_connected():
            raise P3ormException("already connected")

        self.connection = None
        self.pool = await asyncpg.create_pool(
            dsn=dsn,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            **asyncpg_kwargs,  # type: ignore
        )

    async def disconnect(self):
        ...

    def is_connected(self) -> bool:
        if self.connection and not self.connection.is_closed():
            return True

        if self.pool and not self.pool._closed:
            return True

        return False

    def __getitem__(self, table: Type[T]) -> ConnectionExecutor[T]:
        if not issubclass(table, Table):
            raise P3ormException(f"{table=} must be a <p3orm.Table>")

        return ConnectionExecutor(table=table, driver=self)


class Executor(Generic[T], metaclass=abc.ABCMeta):
    table: Type[T]
    driver: Postgres

    def __init__(self, table: Type[T], driver: Postgres):
        self.table = table
        self.driver = driver

    @abc.abstractmethod
    async def execute(self, query: str | QueryBuilder, query_args: list[Any] | None = None) -> list[T]:
        ...


def insert_vals(table: Type[T], items: list[T]) -> tuple[list[str], list[list[Any]]]:
    columns = []
    values = [[] for _ in range(len(items))]

    for field_name, field in table.__memo__.fields.items():
        if field.db_gen:
            continue

        columns.append(field.column_name)

        for i, item in enumerate(items):
            field_value = getattr(item, field_name)

            if field.db_gen:
                if type(field_value) != DB_GENERATED:
                    raise P3ormException(f"{field_name=} is db_gen but not DB_GENERATED")
                continue

            values[i].append(field_value)

    return columns, values


class ConnectionExecutor(Executor, Generic[T]):
    table: Type[T]
    driver: Postgres

    async def execute(
        self,
        query: str | QueryBuilder,
        query_args: list[Any] | None = None,
    ) -> list[T]:
        if isinstance(query, QueryBuilder):
            query = query.get_sql()

        if not self.driver.is_connected():
            raise P3ormException("not connected")

        records: list[asyncpg.Record]

        print(f"\n\n{query=}\n\n")

        if connection := self.driver.connection:  # type: ignore
            records = await connection.fetch(query, *(query_args or []))

        elif self.driver.pool:
            async with self.driver.pool.acquire() as connection:
                connection: asyncpg.Connection
                records = await connection.fetch(query, *(query_args or []))

        else:
            raise P3ormException("not connected. driver has no pool or connection")

        return [
            self.table.__memo__.factory(**{self.table.__memo__.record_kwarg_map[k]: v for k, v in record.items()})
            for record in records
        ]

    async def fetch_all(
        self,
        /,
        criterion: Criterion | None = None,
        *,
        order: pypika.Order | None = None,
        by: pypika.Field | list[pypika.Field] | None = None,
        limit: int | None = None,
    ) -> list[T]:
        query = self.table.select()

        query_args = None
        if criterion:
            parameterized_criterion, query_args = parameterize(criterion)
            query = query.where(parameterized_criterion)

        if by:
            query = query.orderby(
                *(by if isinstance(by, list) else [by]),
                **({"order": order} if order else {}),
            )

        if limit is not None:
            query = query.limit(limit)

        records = await self.execute(query, query_args)

        return records

    async def fetch_one(
        self,
        /,
        criterion: Criterion | None = None,
    ) -> T:
        query: QueryBuilder = self.table.select()

        query_args = []
        if criterion:
            paramaterized_criterion, query_args = parameterize(criterion)
            query = query.where(paramaterized_criterion)

        query = query.limit(2)

        records = await self.execute(query, query_args)

        if len(records) != 1:
            raise P3ormException(
                f"expected one result in {self.table.__name__} where {criterion=}, found {len(records)}"
            )

        return records[0]

    async def fetch_first(
        self,
        /,
        criterion: Criterion | None = None,
    ) -> T | None:
        query = self.table.select()
        query_args = None
        if criterion:
            parameterized_criterion, query_args = parameterize(criterion)
            query = query.where(parameterized_criterion)

        query = query.limit(1)

        records = await self.execute(query, query_args)

        if len(records) == 0:
            return None

        return records[0]

    async def insert(
        self,
        /,
        items: list[T],
    ) -> list[T]:
        columns, values = insert_vals(self.table, items)
        columns_count = len(columns)

        query: PostgreSQLQueryBuilder = PostgreSQLQuery.into(self.table.__tablename__).columns(*columns)
        query_args: list[Any] = []
        for page, args in enumerate(values):
            query = query.insert(*[Parameter(f"${i + 1 + columns_count * page}") for i in range(columns_count)])
            query_args += args

        query = query.returning("*")

        inserted = await self.execute(query, query_args)

        return inserted

    async def update_one(
        self,
        /,
        item: T,
    ) -> T:
        query = self.table.update()

        for pk in self.table.__memo__.pk:
            query = query.where(pk._pypika_field == getattr(item, pk._field_name))

        columns, [values] = insert_vals(self.table, [item])

        for i, column in enumerate(columns):
            query = query.set(column, Parameter(f"${i + 1}"))

        query = query.returning("*")

        [updated] = await self.execute(query, values)
        return updated

    async def delete(
        self,
        /,
        items: list[T],
    ) -> list[T]:
        query = self.table.delete()

        for pk in self.table.__memo__.pk:
            query = query.where(pk._pypika_field.isin([getattr(item, pk._field_name) for item in items]))

        query = query.returning("*")

        deleted = await self.execute(query)

        return deleted
