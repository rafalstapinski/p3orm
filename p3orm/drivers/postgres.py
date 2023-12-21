from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Generic, Type, TypeVar

import asyncpg
from asyncpg import Connection, Pool
from pypika.queries import Query, QueryBuilder
from pypika.terms import ComplexCriterion, Criterion

from p3orm.drivers.base import Driver
from p3orm.exceptions import P3ormException
from p3orm.table import Table
from p3orm.utils import parameterize

T = TypeVar("T", bound=Table)


class DriverMeta(type):
    def __getitem__(cls, table: Type[Table]):
        ...


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

    async def fetch_one(self, /, criterion: Criterion) -> T:
        ...


class ConnectionExecutor(Executor, Generic[T]):
    table: Type[T]
    driver: Postgres

    async def execute(self, query: str | QueryBuilder, query_args: list[Any] | None = None) -> list[T]:
        if isinstance(query, QueryBuilder):
            query = query.get_sql()

        if not self.driver.is_connected():
            raise P3ormException("not connected")

        records: list[asyncpg.Record]

        if connection := self.driver.connection:  # type: ignore
            records = await connection.fetch(query, *(query_args or []))

        elif self.driver.pool:
            async with self.driver.pool.acquire() as connection:
                print(f"{connection=} {type(connection)=}")

                connection: asyncpg.Connection
                records = await connection.fetch(query, *(query_args or []))

        else:
            raise P3ormException("not connected. driver has no pool or connection")

        return [
            self.table.__memo__.factory(**{self.table.__memo__.record_kwarg_map[k]: v for k, v in record.items()})
            for record in records
        ]

    async def fetch_one(self, /, criterion: Criterion) -> T:
        parameterized_criterion, query_args = parameterize(criterion)

        query: QueryBuilder = self.table.select().where(parameterized_criterion)
        query = query.limit(2)

        records = await self.execute(query, query_args)

        if len(records) == 0:
            raise P3ormException(f"no records found for {self.table.__name__} with {criterion=}")

        if len(records) > 1:
            raise P3ormException(f"more than one record found for {self.table.__name__} with {criterion=}")

        return records[0]
