from typing import Any, Type

from asyncpg import Connection, Record, connect

from p3orm.types import Model
from p3orm.utils import record_to_kwargs


class _Porm:

    connection: Connection

    async def connect(
        self,
        dsn: str = None,
        *,
        user: str = None,
        password: str = None,
        database: str = None,
        host: str = None,
        port: int = None,
        **asyncpg_kwargs: dict[str, Any]
    ):
        self.connection = await connect(
            dsn=dsn,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            **asyncpg_kwargs,
        )

    async def disconnect(self):
        await self.connection.close()

    async def fetch_one(self, query: str, table: Type[Model]) -> Model:
        resp: Record = await self.connection.fetchrow(query)

        if resp is None:
            return None

        return table(**record_to_kwargs(resp))

    async def fetch_many(self, query: str, table: Type[Model]) -> list[Model]:
        resp = await self.connection.fetch(query)
        return [table(**record_to_kwargs(row)) for row in resp]


Porm = _Porm()
