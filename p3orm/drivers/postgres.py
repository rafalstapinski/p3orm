from __future__ import annotations

from collections import defaultdict
from types import TracebackType
from typing import Any, DefaultDict, Self, Sequence, Type, TypeVar, cast, get_args

import asyncpg
from pypika.dialects import PostgreSQLQuery, PostgreSQLQueryBuilder
from pypika.enums import Order
from pypika.queries import QueryBuilder
from pypika.terms import Criterion
from pypika.terms import Field as PyPikaField
from pypika.terms import Parameter

from p3orm.drivers.base import Driver
from p3orm.exceptions import P3ormException
from p3orm.fields import PormRelationship, RelationshipType
from p3orm.table import DB_GENERATED
from p3orm.utils import parameterize

T = TypeVar("T")
U = TypeVar("U")


class Executor:
    connection: asyncpg.Connection | None = None
    pool: asyncpg.Pool | None = None

    def is_connected(self) -> bool:
        raise NotImplementedError

    async def execute(self, table: Type[T], query: str | QueryBuilder, query_args: list[Any] | None = None) -> list[T]:
        if isinstance(query, QueryBuilder):
            query = query.get_sql()

        if not self.is_connected():
            raise P3ormException("not connected")

        records: list[asyncpg.Record]

        if self.connection:
            records = await self.connection.fetch(query, *(query_args or []))

        elif self.pool:
            async with self.pool.acquire() as connection:
                records = await connection.fetch(query, *(query_args or []))

        else:
            raise P3ormException("not connected. driver has no pool or connection")

        return [
            table.__memo__.factory(**{table.__memo__.record_kwarg_map[k]: v for k, v in record.items()})
            for record in records
        ]

    async def fetch_all(
        self,
        /,
        table: Type[T],
        criterion: Criterion | None = None,
        *,
        order: Order | None = None,
        by: PyPikaField | list[PyPikaField] | None = None,
        limit: int | None = None,
    ) -> list[T]:
        if criterion is not None and not isinstance(criterion, Criterion):
            raise P3ormException(f"{criterion=} must be instance of Criterion. did you wrap the field with `f()`?")

        query = table.select()

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

        records = await self.execute(table, query, query_args)

        return records

    async def fetch_one(
        self,
        /,
        table: Type[T],
        criterion: Criterion | None = None,
    ) -> T:
        query: QueryBuilder = table.select()

        query_args: list[Any] = []
        if criterion:
            paramaterized_criterion, query_args = parameterize(criterion)
            query = query.where(paramaterized_criterion)

        query = query.limit(2)

        records = await self.execute(table, query, query_args)

        if len(records) != 1:
            raise P3ormException(f"expected one result in {table.__name__} where {criterion=}, found {len(records)}")

        return records[0]

    async def fetch_first(
        self,
        /,
        table: Type[T],
        criterion: Criterion | None = None,
    ) -> T | None:
        query = table.select()
        query_args = None
        if criterion:
            parameterized_criterion, query_args = parameterize(criterion)
            query = query.where(parameterized_criterion)

        query = query.limit(1)

        records = await self.execute(table, query, query_args)

        if len(records) == 0:
            return None

        return records[0]

    async def insert_one(self, /, table: Type[T], item: T) -> T:
        columns, [values] = _insert_vals(table, [item])

        query: PostgreSQLQueryBuilder = PostgreSQLQuery.into(table.__tablename__).columns(*columns)
        query = query.insert(*[Parameter(f"${i + 1}") for i in range(len(columns))])
        query = query.returning("*")

        [inserted] = await self.execute(table, query, values)

        return inserted

    async def insert_many(
        self,
        /,
        table: Type[T],
        items: list[T],
    ) -> list[T]:
        columns, values = _insert_vals(table, items)
        columns_count = len(columns)

        query: PostgreSQLQueryBuilder = PostgreSQLQuery.into(table.__tablename__).columns(*columns)
        query_args: list[Any] = []
        for page, args in enumerate(values):
            query = query.insert(*[Parameter(f"${i + 1 + columns_count * page}") for i in range(columns_count)])
            query_args += args

        query = query.returning("*")

        inserted = await self.execute(table, query, query_args)

        return inserted

    async def update_one(
        self,
        /,
        table: Type[T],
        item: T,
    ) -> T:
        query = table.update()

        for pk in table.__memo__.pk:
            query = query.where(pk._pypika_field == getattr(item, pk._field_name))

        columns, [values] = _insert_vals(table, [item])

        for i, column in enumerate(columns):
            query = query.set(column, Parameter(f"${i + 1}"))

        query = query.returning("*")

        [updated] = await self.execute(table, query, values)
        return updated

    async def delete(
        self,
        /,
        table: Type[T],
        items: list[T],
    ) -> list[T]:
        query = table.delete()

        for pk in table.__memo__.pk:
            query = query.where(pk._pypika_field.isin([getattr(item, pk._field_name) for item in items]))

        query = query.returning("*")

        deleted = await self.execute(table, query)

        return deleted

    async def fetch_related(self, /, table: Type[T], items: list[T], relations: Sequence[Sequence[U]]) -> list[T]:
        if pool := self.pool:
            connection = await self.pool.acquire()

        elif not (connection := self.connection):
            raise P3ormException("not connected")

        try:
            for relationships in relations:
                for relationships in relations:
                    await _load_relationships(table, items, relationships, connection)  # type: ignore

        finally:
            if pool := self.pool:
                await pool.release(connection)

        return items


class Postgres(Driver, Executor):
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
    ) -> None:
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
    ) -> None:
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

    async def disconnect(self) -> None:
        if not self.is_connected():
            raise P3ormException("not connected")

        if self.connection:
            await self.connection.close()
            self.connection = None

        if self.pool:
            await self.pool.close()
            self.pool = None

    def is_connected(self) -> bool:
        if self.connection and not self.connection.is_closed():
            return True

        if self.pool and not self.pool._closed:
            return True

        return False

    def transaction(self) -> TransactionExecutor:
        return TransactionExecutor(self)


class TransactionExecutor(Executor):
    driver: Postgres
    connection: asyncpg.Connection
    transaction: asyncpg.connection.transaction.Transaction

    def __init__(self, driver: Postgres):
        self.driver = driver

    async def __aenter__(self) -> Self:
        if self.driver.connection:
            self.connection = self.driver.connection
        elif self.driver.pool:
            self.connection = await self.driver.pool.acquire()
        else:
            raise P3ormException("not connected")

        self.transaction = self.connection.transaction()
        await self.transaction.start()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self.transaction.commit()
        else:
            await self.transaction.rollback()

        if self.driver.pool:
            await self.driver.pool.release(self.connection)

    def is_connected(self) -> bool:
        driver: Postgres = self.driver
        return driver.is_connected()


def _insert_vals(table: Type[T], items: list[T]) -> tuple[list[str], list[list[Any]]]:
    columns = []
    values: list[list[Any]] = [[] for _ in range(len(items))]

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


async def _load_relationships(
    table: Type[T],
    items: list[T],
    relationships: Sequence[PormRelationship[U]],
    connection: asyncpg.Connection,
) -> None:
    for relationship in relationships:
        items = cast(list[T], await _load_relationship_for_items(table, items, relationship, connection))
        table = relationship._data_type  # type: ignore


async def _load_relationship_for_items(
    table: Type[T],
    items: list[T],
    relationship: PormRelationship[U],
    connection: asyncpg.Connection,
) -> list[U]:
    # short circuit here to avoid doing an IN on an empty list
    if not items:
        return []

    foreign_table = cast(
        Type[U],
        relationship._data_type
        if relationship.relationship_type == RelationshipType.foreign_key
        else get_args(relationship._data_type)[0],
    )

    self_field = table.__memo__.columns[relationship.self_column]
    self_keys = [getattr(item, self_field._field_name) for item in items]

    parameterized_criterion, query_args = parameterize(PyPikaField(relationship.foreign_column).isin(self_keys))
    query: PostgreSQLQueryBuilder = foreign_table.select().distinct().where(parameterized_criterion)

    records = await connection.fetch(query.get_sql(), *query_args or [])
    related_items: list[U] = []

    # TODO: set related relationship to item on related items
    if relationship.relationship_type == RelationshipType.foreign_key:
        related_item_map: dict[Any, U] = {
            record[relationship.foreign_column]: foreign_table.__memo__.factory(
                **{foreign_table.__memo__.record_kwarg_map[k]: v for k, v in record.items()}
            )
            for record in records
        }

        related_items = list(related_item_map.values())

        for item in items:
            setattr(
                item,
                relationship._field_name,
                related_item_map.get(getattr(item, self_field._field_name), None),
            )

    else:
        related_items_map: DefaultDict[Any, list[U]] = defaultdict(list)
        [
            related_items_map[record.get(relationship.foreign_column)].append(  # type: ignore
                foreign_table.__memo__.factory(
                    **{foreign_table.__memo__.record_kwarg_map[k]: v for k, v in record.items()}
                )
            )
            for record in records
        ]

        for item in items:
            setattr(
                item,
                relationship._field_name,
                related_items_map.get(getattr(item, self_field._field_name), []),
            )

        related_items = [ri for ris in related_items_map.values() for ri in ris]

    return related_items
