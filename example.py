import os
from datetime import datetime
from typing import Optional

from pypika.queries import QueryBuilder

from porm.core import Porm
from porm.table import PormField, Table


async def run():
    class Example(Table):
        __tablename__ = "example"

        """ end state might be something like:
        id: int = PormField("id", pk=True)
        name: str = PormField("name")
        """

        id: int = PormField(int, "id", pk=True, autogen=True)
        name: str = PormField(str, "name")
        created_at: datetime = PormField(datetime, "created_at", autogen=True)

    await Porm.connect(dsn=os.environ["DSN"])

    query: QueryBuilder = Example.select().where(Example.id < 10)

    # r: Example = (await Porm.fetch_many(query.get_sql(), Example))[0]

    r: Example = await Example.get(Example.id == 4)
    # print(r)

    # r = await Example.fetch_many(Example.id < 10)
    # print(r)

    # r = await Example.insert_one(Example(name="test1"))

    print(r)

    r.name = "yeet"

    r = await Example.update_one(r)
    print(r)
    # r.id = 12


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
