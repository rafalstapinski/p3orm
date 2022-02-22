from typing import Any, Dict, List, Optional, Type, Union

from asyncpg import Connection, Pool, Record, connect, create_pool
from pypika.queries import QueryBuilder

from p3orm.exceptions import AlreadyConnected, NotConnected
from p3orm.types import Model
from p3orm.utils import record_to_kwargs


class _Porm:

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
        **asyncpg_kwargs: Dict[str, Any]
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
        **asyncpg_kwargs: Dict[str, Any]
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

    async def fetch_one(self, query: Union[str, QueryBuilder], table: Type[Model]) -> Optional[Model]:
        results = await self.fetch_many(query, table)
        return None if len(results) == 0 else results[0]

    async def fetch_many(self, query: Union[str, QueryBuilder], table: Type[Model]) -> List[Model]:

        if isinstance(query, QueryBuilder):
            query = query.get_sql()

        if not self.is_connected():
            raise NotConnected("No database connection or pool is established")

        results = []
        if self.connection:
            results = await self.connection.fetch(query)
        elif self.pool:
            async with self.pool.acquire() as connection:
                connection: Connection
                results = await connection.fetch(query)

        return [table(**record_to_kwargs(row)) for row in results]

    def is_connected(self) -> bool:

        if self.connection and not self.connection.is_closed():
            return True

        if self.pool and not self.pool._closed:
            print(self.pool, self.pool._closed)
            return True

        return False


Porm = _Porm()
