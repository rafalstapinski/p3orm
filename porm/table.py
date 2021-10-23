from typing import Any, Final, Optional

from asyncpg.types import Type
from pydantic.main import create_model
from pypika import Query
from pypika.queries import QueryBuilder
from pypika.terms import BasicCriterion, Field

from porm.core import Porm
from porm.types import ModelFactory, TableModel
from porm.utils import with_returning


class PormField(Field):

    name: str
    data_type: Final[Type]
    pk: bool

    def __init__(self, data_type: Type, name: str, pk: Optional[bool] = False):
        self.name = name  # also used by pypika
        self.data_type = data_type
        self.pk = pk


class Table:

    __tablename__: str

    # magic stuff
    def __new__(cls, /, **create_fields) -> TableModel:

        self = super().__new__(cls)

        model_factory = self._create_model_factory()
        return model_factory(**create_fields)

    def _create_model_factory(self) -> ModelFactory:

        factory_model_kwargs = {}
        for field in self._db_fields():
            factory_model_kwargs[field.name] = (field.data_type, ...)

        return create_model(self.__class__.__name__, **factory_model_kwargs)

    def __init_subclass__(cls) -> None:
        self = super().__new__(cls)
        if not hasattr(self, "__tablename__") or self.__tablename__ is None:
            raise Exception(f"{self.__class__.__name__} must define a __tablename__ property")

    def _db_fields(self) -> list[PormField]:
        return [field for field_name in self.__dir__() if isinstance(field := getattr(self, field_name), PormField)]

    def _db_values(self, item: TableModel) -> list[Any]:
        return [getattr(item, field.name) for field in self._db_fields()]

    # def __setattr__(self, name: str, value: Any) -> None:
    #     if not hasattr(self, name):
    #         raise Exception(f"Attribute {name} doesn't exist on {self.__class__.__name__}")

    #     attr = getattr(name)
    #     if not isinstance(attr, PormField):
    #         raise Exception(f"Can't set {name} on {self.__class__.__name__}")

    #     if attr.pk:
    #         raise Exception(f"Can't override primary key of {self.__class__.__name__}")

    #     super().__setattr__(name, value)

    # db operators
    @classmethod
    def from_(cls) -> QueryBuilder:
        self = super().__new__(cls)
        return Query.from_(self.__tablename__)

    @classmethod
    def select(cls) -> QueryBuilder:
        return cls.from_().select("*")

    @classmethod
    async def first(cls, query: QueryBuilder) -> Optional[TableModel]:
        # run query
        cursor_results = []
        if len(cursor_results) > 0:
            return cls(cursor_results[0])
        return None

    @classmethod
    async def insert_one(cls, item: TableModel) -> TableModel:
        self = super().__new__(cls)
        query: QueryBuilder = Query.into(self.__tablename__).columns(*self._db_fields()).insert(*self._db_values(item))
        return await Porm.fetch_one(
            with_returning(query),
        )

    @classmethod
    async def insert_many(cls, /, *items: list[TableModel]) -> list[TableModel]:
        self = super().__new__(cls)
        query: QueryBuilder = Query.info(self.__tablename__).columns(*self._db_fields())

        for item in items:
            query = query.insert(*self._db_values(item))

        return await Porm.fetch_many(with_returning(query), self._create_model_factory())

    @classmethod
    async def fetch_first(cls, /, criterion: BasicCriterion) -> Optional[TableModel]:
        self = super().__new__(cls)
        query: QueryBuilder = cls.select().where(criterion)
        query = query.limit(1)

        return await Porm.fetch_one(query.get_sql(), cls)

    @classmethod
    async def fetch_many(cls, /, criterion: BasicCriterion) -> list[TableModel]:
        self = super().__new__(cls)
        query: QueryBuilder = cls.select().where(criterion)

        return await Porm.fetch_many(query.get_sql(), cls)

    @classmethod
    def update(cls, item: TableModel) -> TableModel:
        self = super().__new__(cls)

    @classmethod
    def update(cls, /, *items: TableModel) -> TableModel:
        ...

        # run query

    @classmethod
    def query(cls, query: QueryBuilder, response: TableModel | list[TableModel]):
        ...
