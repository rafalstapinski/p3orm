from typing import TypeVar

from p3orm.drivers.base import Driver
from p3orm.table import Table

T = TypeVar("T", bound=Table)


class Postgres(Driver):
    def __init__(self):
        ...

    async def connect(self):
        ...

    async def connect_pool(self):
        ...

    async def disconnect(self):
        ...

    #
    # async def __aenter__(self):
    #     ...
    #
    # async def __aexit__(self, exc_type, exc_value, tb):
    #     ...
    #
    # def transaction(self):
    #     ...

    async def fetch_one[T](self, condition) -> T:
        ...
