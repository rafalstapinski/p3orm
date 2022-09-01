from typing import Any, List, Optional, Sequence, Type, Union

from pypika.queries import QueryBuilder

from p3orm.types import Model


class BaseDriver:
    async def fetch_one(
        self,
        cls: Type[Model],
        query: Union[str, QueryBuilder],
        query_args: Sequence[Any] = None,
    ) -> Optional[Model]:
        raise NotImplementedError

    async def fetch_many(
        self,
        cls: Type[Model],
        query: Union[str, QueryBuilder],
        query_args: Sequence[Any] = None,
    ) -> List[Model]:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError
