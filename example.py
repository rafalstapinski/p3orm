import os
from datetime import datetime

from pypika.queries import QueryBuilder

from porm.core import Porm
from porm.table import PormField, Table


async def run():
    class Restaurant(Table):
        __tablename__ = "restaurant"

        """ end state might be something like:
        id: int = PormField("id", pk=True)
        name: str = PormField("name")
        """

        id: int = PormField(int, "id", pk=True)
        name: str = PormField(str, "name")
        created_at: datetime = PormField(datetime, "created_at")

    await Porm.connect(dsn=os.environ["DSN"])

    query: QueryBuilder = Restaurant.select().where(Restaurant.id < 10)

    # r: Restaurant = (await Porm.fetch_many(query.get_sql(), Restaurant))[0]

    r = await Restaurant.fetch_first(Restaurant.id == 1)
    print(r)

    r = await Restaurant.fetch_many(Restaurant.id < 10)
    print(r)

    # r.name = "test"
    # r.id = 12


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
