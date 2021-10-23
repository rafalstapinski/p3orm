from typing import Any, List, Optional, TypeVar, Union
import typing
import asyncpg
from asyncpg.types import Type
from pydantic.main import create_model
from pypika import Query
from pydantic import BaseModel
from pypika.queries import QueryBuilder
from pypika.terms import Field


class PormField(Field):

    def __init__(self, data_type: Type, name: str):
        self.name = name # also used by pypika
        self.data_type = data_type


TableModel = Union[TypeVar("TableModel"), BaseModel, "Table"]

class Table:
    __tablename__: str
    
    def __new__(cls, /, **create_fields) -> TableModel:

        self = super().__new__(cls)
        
        create_model_kwargs = {}
        for field in self._fields():
            field_value = create_fields.get(field.name)
            create_model_kwargs[field.name] = (field.data_type, field_value)

        model_factory = create_model(cls.__class__.__name__, **create_model_kwargs)
        model = model_factory(**create_fields)
        return model

    def __init_subclass__(cls) -> None:
        self = super().__new__(cls)
        if not hasattr(self, "__tablename__") or self.__tablename__ is None:
            raise Exception(f"{self.__class__.__name__} must define a __tablename__ property")

    def _fields(self) -> list[PormField]:
        return [field for field_name in self.__dir__() if isinstance(field := getattr(self, field_name), PormField)]
    
    def _values(self, item: TableModel) -> list[Any]:
        return [getattr(item, field.name) for field in self._fields()]

    @classmethod
    def select(cls) -> QueryBuilder:
        self = super().__new__(cls)
        return Query.from_(self.__tablename__).select("*")
    
    @classmethod
    async def first(cls, query: QueryBuilder) -> Optional[TableModel]:
        # run query
        cursor_results = []
        if len(cursor_results) > 0:
            return cls(cursor_results[0])
        return None
    
    @classmethod
    def insert(cls, /, *items: TableModel):
        self = super().__new__(cls)
        query = Query.into(self.__tablename__).columns(*self._fields())

        for item in items:
            query = query.insert(*self._values(item))
        
        # run query
