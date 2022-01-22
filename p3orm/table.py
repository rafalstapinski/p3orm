from typing import Any, Final, Optional, Type, Union

from pydantic.errors import cls_kwargs
from pydantic.main import create_model
from pypika import Query
from pypika.queries import QueryBuilder
from pypika.terms import BasicCriterion, Field

from p3orm.core import Porm
from p3orm.types import Model
from p3orm.utils import with_returning


class PormField(Field):

    name: str
    data_type: Final[Type]
    pk: bool
    autogen: bool

    def __init__(self, data_type: Type, name: str, pk: Optional[bool] = False, autogen: Optional[bool] = False):
        self.name = name  # also used by pypika
        self.data_type = data_type
        self.pk = pk
        self.autogen = autogen


class Table:

    __tablename__: str

    def __new__(cls, /, **create_fields) -> Model:

        model_factory = cls._create_model_factory()
        return model_factory(**create_fields)

    @classmethod
    def _create_model_factory(self) -> Type[Model]:

        factory_model_kwargs = {}
        for field in self._db_fields():
            factory_model_kwargs[field.name] = (field.data_type, None)

        return create_model(self.__class__.__name__, **factory_model_kwargs)

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "__tablename__") or cls.__tablename__ is None:
            raise Exception(f"{cls.__class__.__name__} must define a __tablename__ property")

    @classmethod
    def _db_fields(cls, exclude_autogen: Optional[bool] = False) -> list[PormField]:
        fields = [field for field_name in cls.__dict__ if isinstance(field := getattr(cls, field_name), PormField)]
        if exclude_autogen:
            fields = [f for f in fields if not f.autogen]
        return fields

    @classmethod
    def _db_values(cls, item: Model, exclude_autogen: Optional[bool] = False) -> list[Any]:
        return [getattr(item, field.name) for field in cls._db_fields(exclude_autogen=exclude_autogen)]

    @classmethod
    def _primary_key(cls) -> Optional[PormField]:
        for field in cls._db_fields():
            if field.pk:
                return field
        return None

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
        return Query.from_(cls.__tablename__)

    @classmethod
    def select(cls) -> QueryBuilder:
        return cls.from_().select("*")

    @classmethod
    async def first(cls: Type[Model] | "Table", query: QueryBuilder) -> Optional[Model]:
        # run query
        cursor_results = []
        if len(cursor_results) > 0:
            return cls(cursor_results[0])
        return None

    @classmethod
    async def insert_one(cls: Type[Model] | "Table", item: Model) -> Model:
        query: QueryBuilder = (
            Query.into(cls.__tablename__)
            .columns(cls._db_fields(exclude_autogen=True))
            .insert(*cls._db_values(item, exclude_autogen=True))
        )
        return await Porm.fetch_one(with_returning(query), cls)

    @classmethod
    async def insert_many(cls: Type[Model] | "Table", /, *items: list[Model]) -> list[Model]:
        query: QueryBuilder = Query.info(cls.__tablename__).columns(*cls._db_fields())

        for item in items:
            query = query.insert(*cls._db_values(item))

        return await Porm.fetch_many(with_returning(query), cls)

    @classmethod
    async def fetch_first(cls: Type[Model] | "Table", /, criterion: BasicCriterion) -> Optional[Model]:
        query: QueryBuilder = cls.select().where(criterion)
        query = query.limit(1)
        return await Porm.fetch_one(query.get_sql(), cls)

    @classmethod
    async def get(cls: Type[Model] | "Table", /, criterion: BasicCriterion) -> Model:
        query: QueryBuilder = cls.select().where(criterion)
        query = query.limit(2)
        results = await Porm.fetch_many(query.get_sql(), cls)
        if len(results) > 1:
            raise Exception("Multiple objects were returned from get query")

        return results[0]

    @classmethod
    async def fetch_many(cls: Type[Model] | "Table", /, criterion: BasicCriterion) -> list[Model]:
        query: QueryBuilder = cls.select().where(criterion)
        return await Porm.fetch_many(query.get_sql(), cls)

    @classmethod
    async def update_one(cls: Type[Model] | "Table", item: Model) -> Model:
        query: QueryBuilder = Query.update(cls.__tablename__)

        for field in cls._db_fields():
            query = query.set(field.name, getattr(item, field.name))

        pk = cls._primary_key()

        if not pk:
            raise Exception("Can't update without primary key rn")

        query = query.where(pk == getattr(item, pk.name))

        return await Porm.fetch_one(with_returning(query), cls)
