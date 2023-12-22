from __future__ import annotations

from typing import Type, TypeVar

from p3orm.table import Table

T = TypeVar("T", bound=Table)


class Driver:
    tables: list[Type[T]]

    def __init__(self, tables: list[Type[T]]) -> None:
        super().__init__()
        self.tables = tables
        for table in tables:
            table._init_stuff(self)

    #
    # @abstractmethod
    # async def execute_many(self):
    #     ...
    #
    # @abstractmethod
    # async def execute_one(self):
    #     ...
    #
    # @abstractmethod
    # async def fetch_one(self):
    #     ...

    #
    # @abstractmethod
    # async def fetch_first(self):
    #     ...
    #
    # @abstractmethod
    # async def fetch_many(self):
    #     ...
    #
    # @abstractmethod
    # async def insert_one(self):
    #     ...
    #
    # @abstractmethod
    # async def insert_many(self):
    #     ...
    #
    # @abstractmethod
    # async def update_one(self):
    #     ...
    #
    # @abstractmethod
    # async def update_many(self):
    #     ...
    #
    # @abstractmethod
    # async def delete_one(self):
    #     ...
    #
    # @abstractmethod
    # async def delete_many(self):
    #     ...
    #
    # @abstractmethod
    # async def fetch_related(self):
    #     ...
    #     """
    #     for inserts and updates, use AliasedQuery with the .with to create a subquery that can be inserted into the parent quer to do prefetching.
    #     pypika docs, tutorial -> with clause
    #     """
