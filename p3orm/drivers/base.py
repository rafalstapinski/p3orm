from abc import ABC, abstractmethod
from typing import TypeVar

from p3orm.table import Table

T = TypeVar("T", bound=Table)


class Driver(ABC):
    ...

    @abstractmethod
    async def execute_many(self):
        ...

    @abstractmethod
    async def execute_one(self):
        ...

    @abstractmethod
    async def fetch_one(self):
        ...

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
