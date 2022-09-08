from typing import Any, Dict, List, Optional, Sequence, Type, Union

from asyncpg import Connection, Pool, Record, connect, create_pool
from asyncpg.pool import PoolAcquireContext
from pypika.queries import QueryBuilder

from p3orm.drivers.base import BaseDriver
from p3orm.exceptions import AlreadyConnected, NotConnected
from p3orm.types import Model
from p3orm.utils import record_to_kwargs


class ConnectionContext:

    connection: Connection

    def __init__(self, connection: Connection):
        self.connection = connection

    async def __aenter__(self) -> Connection:
        return self.connection

    async def __aexit__(self, *exc):
        self.connection = None


class PoolConnectionContext(PoolAcquireContext):
    async def __aenter__(self) -> Connection:
        return await super().__aenter__()


class PostgresDriver(BaseDriver):

    connection: Connection
    pool: Pool

    def __init__(self):
        self.connection = None
        self.pool = None

    async def connect(
        self,
        dsn: str = None,
        *,
        user: str = None,
        password: str = None,
        database: str = None,
        host: str = None,
        port: int = None,
        **asyncpg_kwargs: Dict[str, Any],
    ):
        if self.is_connected():
            raise AlreadyConnected("A connection or pool is already established")

        self.pool = None
        self.connection = await connect(
            dsn=dsn,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            **asyncpg_kwargs,
        )

    async def connect_pool(
        self,
        dsn: str = None,
        *,
        user: str = None,
        password: str = None,
        database: str = None,
        host: str = None,
        port: int = None,
        **asyncpg_kwargs: Dict[str, Any],
    ):
        if self.is_connected():
            raise AlreadyConnected("A databse connection or pool is already established")

        self.connection = None
        self.pool = await create_pool(
            dsn=dsn,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            **asyncpg_kwargs,
        )

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

        if self.pool:
            await self.pool.close()

        self.connection = None
        self.pool = None

    async def fetch_one(
        self,
        cls: Type[Model],
        query: Union[str, QueryBuilder],
        query_args: Sequence[Any] = None,
    ) -> Optional[Model]:
        results = await self.fetch_many(cls, query, query_args=query_args)
        return None if len(results) == 0 else results[0]

    async def fetch_many(
        self,
        cls: Type[Model],
        query: Union[str, QueryBuilder],
        query_args: Sequence[Any] = None,
    ) -> List[Model]:

        if isinstance(query, QueryBuilder):
            query = query.get_sql()

        if not self.is_connected():
            raise NotConnected("No database connection or pool is established")

        fetch_arguments = [query]

        if query_args:
            fetch_arguments += query_args

        results: List[Record] = []

        async with self._acquire_connection() as connection:
            results = await connection.fetch(*fetch_arguments)

        return [cls(**record_to_kwargs(row)) for row in results]

    def _acquire_connection(self) -> Union[ConnectionContext, PoolConnectionContext]:

        if self.connection:
            return ConnectionContext(self.connection)

        elif self.pool:
            return self.pool.acquire()

        raise NotConnected("No database connection or pool is established")

    def is_connected(self) -> bool:

        if self.connection and not self.connection.is_closed():
            return True

        if self.pool and not self.pool._closed:
            return True

        return False
