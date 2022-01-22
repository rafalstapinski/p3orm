from typing import Type

import asyncpg

from p3orm.types import Model
from p3orm.utils import record_to_kwargs


class _Porm:

    connection: asyncpg.Connection
    # pool: asyncpg.Pool

    async def connect(
        self,
        dsn: str = None,
        *,
        user: str = None,
        password: str = None,
        database: str = None,
        host: str = None,
        port: int = None
    ):
        self.connection = await asyncpg.connect(
            dsn=dsn, host=host, port=port, user=user, password=password, database=database
        )

    async def disconnect(self):
        await self.connection.close()

    async def fetch_one(self, query: str, model: Type[Model]) -> Model:
        resp: asyncpg.Record = await self.connection.fetchrow(query)
        return model(**record_to_kwargs(resp))

    async def fetch_many(self, query: str, model: Type[Model]) -> list[Model]:
        resp = await self.connection.fetch(query)
        return [model(**record_to_kwargs(row)) for row in resp]


Porm = _Porm()
