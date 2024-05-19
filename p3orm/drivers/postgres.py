from __future__ import annotations

from collections import defaultdict
from types import TracebackType
from typing import Any, Callable, Coroutine, DefaultDict, Self, Sequence, Type, TypeVar, cast

import asyncpg
from pypika import functions as fn
from pypika.dialects import PostgreSQLQuery, PostgreSQLQueryBuilder
from pypika.enums import Order
from pypika.queries import QueryBuilder
from pypika.terms import Criterion
from pypika.terms import Field as PyPikaField
from pypika.terms import Parameter

from p3orm.drivers.base import Driver
from p3orm.exceptions import P3ormException
from p3orm.fields import DEFAULT, PormRelationship, RelationshipType
from p3orm.table import DB_GENERATED, Table
from p3orm.utils import cast_enum, get_base_type, is_field_enum, is_field_pydantic, parameterize

T = TypeVar("T", bound="Table")
U = TypeVar("U", bound="Table")
RELATIONS_TYPE = Sequence[Sequence[U]]


# NOTE: just here for type hinting on Postgres.acquire()
class ConnectionContext:
    connection: asyncpg.Connection

    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection

    async def __aenter__(self) -> asyncpg.Connection:
        return self.connection

    async def __aexit__(self, *exc):
        self.connection = None  # type: ignore


class Executor:
    connection: asyncpg.Connection | None = None
    pool: asyncpg.Pool | None = None

    def is_connected(self) -> bool:
        raise NotImplementedError

    async def execute_raw(self, query: str | QueryBuilder, query_args: list[Any] | None = None) -> list[asyncpg.Record]:
        if isinstance(query, QueryBuilder):
            query = query.get_sql()

        if not self.is_connected():
            raise P3ormException("not connected")

        records: list[asyncpg.Record]

        if self.connection:
            records = await self.connection.fetch(query, *query_args or [])

        elif self.pool:
            async with self.pool.acquire() as connection:
                records = await connection.fetch(query, *query_args or [])

        else:
            raise P3ormException("not connected. driver has no pool or connection")

        return records

    async def execute(self, table: Type[T], query: str | QueryBuilder, query_args: list[Any] | None = None) -> list[T]:
        if isinstance(query, QueryBuilder):
            query = query.get_sql()

        if not self.is_connected():
            raise P3ormException("not connected")

        records: list[asyncpg.Record]

        # i hate this for now and i will eventually tap into the actual fields query building but for now:
        query = query.replace(" IN ()", " IN (NULL)")
        query_args = query_args or []

        async with self.acquire() as connection:
            records = await connection.fetch(query, *query_args)

        return [_turn_record_into_orm_instance(table, record) for record in records]

    async def count(
        self,
        /,
        table: Type[Table],
        criterion: Criterion | None = None,
    ) -> int:
        if criterion is not None and not isinstance(criterion, Criterion):
            raise P3ormException(f"{criterion=} must be instance of Criterion. did you wrap the field with `f()`?")

        query = table.select(fn.Count("*"))
        query_args = None
        if criterion:
            parameterized_criterion, query_args = parameterize(criterion)
            query = query.where(parameterized_criterion)

        res = await self.execute_raw(query, query_args)

        return res[0]["count"]

    async def fetch_all(
        self,
        /,
        table: Type[T],
        criterion: Criterion | None = None,
        *,
        order: Order | None = None,
        by: PyPikaField | list[PyPikaField] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        prefetch: RELATIONS_TYPE | None = None,
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

        if offset is not None:
            query = query.offset(offset)

        records = await self.execute(table, query, query_args)

        if prefetch:
            await self.fetch_related(table, records, prefetch)

        return records

    async def fetch_one(
        self,
        /,
        table: Type[T],
        criterion: Criterion | None = None,
        *,
        prefetch: RELATIONS_TYPE | None = None,
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

        if prefetch:
            await self.fetch_related(table, records, prefetch)

        return records[0]

    async def fetch_first(
        self,
        /,
        table: Type[T],
        criterion: Criterion | None = None,
        *,
        prefetch: RELATIONS_TYPE | None = None,
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

        if prefetch:
            await self.fetch_related(table, records, prefetch)

        return records[0]

    async def insert_one(
        self,
        /,
        table: Type[T],
        item: T,
        *,
        prefetch: RELATIONS_TYPE | None = None,
    ) -> T:
        columns, [params], query_args = _insert_vals(table, [item])

        query: PostgreSQLQueryBuilder = PostgreSQLQuery.into(table.__tablename__).columns(*columns)
        query = query.insert(*params)
        query = query.returning("*")

        [record] = await self.execute(table, query, query_args)

        if prefetch:
            await self.fetch_related(table, [record], prefetch)

        return record

    async def insert_many(
        self,
        /,
        table: Type[T],
        items: list[T],
        *,
        prefetch: RELATIONS_TYPE | None = None,
    ) -> list[T]:
        if not items:
            return []

        columns, params_list, query_args = _insert_vals(table, items)

        query: PostgreSQLQueryBuilder = PostgreSQLQuery.into(table.__tablename__).columns(*columns)

        for params in params_list:
            query = query.insert(*params)

        query = query.returning("*")

        records = await self.execute(table, query, query_args)

        if prefetch:
            await self.fetch_related(table, records, prefetch)

        return records

    async def update_one(
        self,
        /,
        table: Type[T],
        item: T,
        *,
        prefetch: RELATIONS_TYPE | None = None,
    ) -> T:
        query = table.update()

        for pk in table.__memo__.pk:
            query = query.where(pk._pypika_field == getattr(item, pk._field_name))

        columns, [params], query_args = _insert_vals(table, [item])

        for i, column in enumerate(columns):
            query = query.set(column, params[i])

        query = query.returning("*")

        [record] = await self.execute(table, query, query_args)

        if prefetch:
            await self.fetch_related(table, [record], prefetch)

        return record

    async def delete(
        self,
        /,
        table: Type[T],
        items: list[T],
    ) -> list[T]:
        if not items:
            return []

        query = table.delete()

        for pk in table.__memo__.pk:
            query = query.where(pk._pypika_field.isin([getattr(item, pk._field_name) for item in items]))

        query = query.returning("*")

        record = await self.execute(table, query)

        return record

    async def fetch_related(self, /, table: Type[T], items: list[T], relations: RELATIONS_TYPE) -> list[T]:
        if pool := self.pool:
            connection = await self.pool.acquire()

        elif not (connection := self.connection):
            raise P3ormException("not connected")

        try:
            await _fetch_related(table, items, relations, connection)

        finally:
            if pool := self.pool:
                await pool.release(connection)

        return items

    def acquire(self) -> ConnectionContext | asyncpg.pool.PoolAcquireContext:
        if self.connection:
            return ConnectionContext(self.connection)

        elif self.pool:
            return self.pool.acquire()

        raise P3ormException("not connected")


class Postgres(Driver, Executor):
    async def connect(
        self,
        dsn: str | None = None,
        *,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        host: str | None = None,
        port: int | None = None,
        init: Callable[[asyncpg.Connection], Coroutine[None, None, None]] | None = None,
        **asyncpg_kwargs: dict[Any, Any],
    ) -> None:
        if self.is_connected():
            raise P3ormException("already connected")

        self.pool = None
        self.connection = cast(
            asyncpg.Connection,
            await asyncpg.connect(
                dsn=dsn,
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                statement_cache_size=0,
                **asyncpg_kwargs,  # type: ignore
            ),
        )

        if init:
            await init(self.connection)

    async def connect_pool(
        self,
        dsn: str | None = None,
        *,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        host: str | None = None,
        port: int | None = None,
        init: Callable[[asyncpg.Connection], Coroutine[None, None, None]] | None = None,
        min_size: int = 10,
        max_size: int = 10,
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
            statement_cache_size=0,
            init=init,
            min_size=min_size,
            max_size=max_size,
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


def _insert_vals(
    table: Type[T],
    items: list[T],
) -> tuple[list[str], list[list[Any]], list[Any]]:
    columns = []
    args = []
    params: list[list[Any]] = [[] for _ in range(len(items))]

    _table = cast(Type[Table], table)
    for field_name, field in _table.__memo__.fields.items():
        columns.append(field.column_name)

    for i, item in enumerate(items):
        for field_name, field in _table.__memo__.fields.items():
            value = getattr(item, field_name)

            if isinstance(value, DB_GENERATED):
                params[i].append(DEFAULT)
                continue

            if value and is_field_pydantic(field):
                value = value.model_dump_json()
            elif value and is_field_enum(field):
                value = cast_enum(field, value)

            params[i].append(Parameter(f"${len(args) + 1}"))
            args.append(value)

    return columns, params, args


async def _fetch_related(
    table: Type[T], items: list[T], relations: RELATIONS_TYPE, connection: asyncpg.Connection
) -> list[T]:
    FETCHED = []

    for relationships in relations:
        await _load_relationships(table, items, relationships, connection, FETCHED)

    return items


async def _load_relationships(
    table: Type[T],
    items: list[T],
    relationships: Sequence[PormRelationship],
    connection: asyncpg.Connection,
    FETCHED: list[str],
) -> None:
    for relationship in relationships:
        items = await _load_relationship_for_items(table, items, relationship, connection, FETCHED)
        table = relationship._data_type  # type: ignore


def _turn_record_into_orm_instance(table: Type[T], record: asyncpg.Record) -> T:
    field_map = {}
    for column_name, value in record.items():
        if column_name not in table.__memo__.columns:
            continue

        field = table.__memo__.columns[column_name]

        if value and is_field_pydantic(field):
            field_type = get_base_type(field._data_type)
            field_map[column_name] = field_type.model_validate_json(value)
        elif value and is_field_enum(field):
            field_map[column_name] = cast_enum(field, value)
        else:
            field_map[column_name] = value

    return table(**field_map)


async def _load_relationship_for_items(
    table: Type[T],
    items: list[T],
    relationship: PormRelationship[U],
    connection: asyncpg.Connection,
    FETCHED: list[str],
) -> list[U]:
    # short circuit here to avoid doing an IN on an empty list
    if not items:
        return []

    foreign_table = cast(Type[U], get_base_type(relationship._data_type))

    self_field = table.__memo__.columns[relationship.self_column]

    relationship_id = (
        f"{table.__tablename__}.{relationship.self_column}:{foreign_table.__tablename__}.{relationship.foreign_column}"
    )

    if relationship_id in FETCHED:
        fetched_related_items: list[U] = []
        if relationship.is_plural():
            [
                fetched_related_items.extend(getattr(item, relationship._field_name))
                for item in items
                if getattr(item, relationship._field_name)
            ]
        else:
            fetched_related_items = [
                getattr(item, relationship._field_name) for item in items if getattr(item, relationship._field_name)
            ]
        return fetched_related_items
    else:
        FETCHED.append(relationship_id)

    self_keys = [getattr(item, self_field._field_name) for item in items]

    join_condition = PyPikaField(relationship.foreign_column).isin(self_keys)
    if relationship.criterion:
        join_condition &= relationship.criterion

    parameterized_criterion, query_args = parameterize(join_condition)
    query: PostgreSQLQueryBuilder = foreign_table.select().distinct().where(parameterized_criterion)

    records = await connection.fetch(query.get_sql(), *query_args or [])
    related_items: list[U] = []

    # TODO: set related relationship to item on related items
    if relationship.relationship_type in (RelationshipType.foreign_key, RelationshipType.reverse_one):
        related_item_map: dict[Any, U] = {
            record[relationship.foreign_column]: _turn_record_into_orm_instance(foreign_table, record)
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
                _turn_record_into_orm_instance(foreign_table, record)
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
