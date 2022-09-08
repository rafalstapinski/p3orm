import re
from pathlib import Path
from sqlite3 import Row
from typing import Any, Dict, List, Optional, Sequence, Type, Union

import aiosqlite
from aiosqlite.core import Connection
from pypika.queries import QueryBuilder

from p3orm.drivers.base import BaseDriver
from p3orm.exceptions import AlreadyConnected, NotConnected
from p3orm.types import Model


class SqliteDriver(BaseDriver):

    connection: Connection

    def __init__(self):
        self.connection = None

    async def connect(
        self,
        database: Union[str, Path],
        **aiosqlite_kwargs: Dict[str, Any],
    ):
        if self.is_connected():
            raise AlreadyConnected("A connection or pool is already established")

        self.connection = await aiosqlite.connect(database=database, **aiosqlite_kwargs)

    async def disconnect(self):
        await self.connection.close()
        self.connection = None

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

        rows: List[Row] = []
        column_names: List[str] = []
        fields_map = {f.column_name: f.field_name for f in cls._fields()}

        # In a case such as an update, "where" arguments are placed toward the end
        # SQLite doesn't deal well with out of order params that don't match their
        # arguments, so here we shift the arguments a necessary amount so that they
        # match positionally rather than numerically
        params = re.findall(r"\$[0-9]+", query)
        if len(params) > 1:
            rotate_amount = len(params) - params.index("$1")
            for i in range(rotate_amount):
                query_args.append(query_args.pop(0))

        async with self.connection.execute(query, query_args) as cursor:
            rows = await cursor.fetchall()
            column_names = [column[0] for column in cursor.description]

        return [
            cls(**{fields_map[column_name]: column_value for column_name, column_value in zip(column_names, row)})
            for row in rows
        ]

    def is_connected(self) -> bool:
        if not self.connection:
            return False

        if not (self.connection._running and self.connection._connection):
            return False

        return True
