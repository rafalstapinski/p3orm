from __future__ import annotations

from typing import Any, Optional, Type, get_type_hints

from pydantic.main import create_model
from pypika import Query
from pypika.queries import QueryBuilder
from pypika.terms import BasicCriterion, Field

from p3orm.core import Porm
from p3orm.types import Model
from p3orm.utils import with_returning


class PormField(Field):

    pk: bool
    autogen: bool

    def __init__(self, name: str, pk: Optional[bool] = False, autogen: Optional[bool] = False):
        self.name = name  # column name - must match field name as well
        self.pk = pk
        self.autogen = autogen


class Relationship:

    table: Type[Table]
    self_field: str
    other_field: str

    def __init__(self, /, table: Type[Table], *, self_field: str, other_field: str):
        self.table = table
        self.self_field = self_field
        self.other_field = other_field


class ForeignKeyRelationship(Relationship):
    ...


class ReverseRelationship(Relationship):
    ...


class Table:

    __tablename__: str

    #
    # Magic
    #
    def __new__(cls, /, **create_fields) -> Model:
        return cls._create_model_factory()(**create_fields)

    @classmethod
    def _create_model_factory(cls) -> Type[Model]:

        types = get_type_hints(cls)

        factory_model_kwargs = {}
        for field_name in cls._field_map().keys():
            factory_model_kwargs[field_name] = (types[field_name], None)

        return create_model(cls.__name__, **factory_model_kwargs)

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "__tablename__") or cls.__tablename__ is None:
            raise Exception(f"{cls.__name__} must define a __tablename__ property")

        fields = cls._fields()

        if len([f for f in fields if f.pk]) != 1:
            raise Exception(f"{cls.__name__} is missing a primary key")

    #
    # Introspective methods
    #
    @classmethod
    def _relationship_map(cls) -> list[Relationship]:
        return {
            name: relationship for name in cls.__dict__ if isinstance(relationship := getattr(cls, name), Relationship)
        }

    @classmethod
    def _relationship_field_name(cls, relationship: Relationship) -> str:
        for field_name, _relationship in cls._relationship_map():
            if relationship == _relationship:
                return field_name

        raise Exception(f"{relationship=} does not exist on {cls=}")

    @classmethod
    def _fields(cls, exclude_autogen: Optional[bool] = False) -> list[PormField]:
        fields = [field for field_name in cls.__dict__ if isinstance(field := getattr(cls, field_name), PormField)]
        if exclude_autogen:
            fields = [f for f in fields if not f.autogen]
        return fields

    @classmethod
    def _field_map(cls, exclude_autogen: Optional[bool] = False) -> dict[str, PormField]:
        fields = {
            field_name: field for field_name in cls.__dict__ if isinstance(field := getattr(cls, field_name), PormField)
        }
        if exclude_autogen:
            fields = {k: v for k, v in fields.items() if not v.autogen}
        return fields

    @classmethod
    def _db_values(cls, item: Model, exclude_autogen: Optional[bool] = False) -> list[Any]:
        return [getattr(item, field.name) for field in cls._fields(exclude_autogen=exclude_autogen)]

    @classmethod
    def _primary_key(cls) -> Optional[PormField]:
        for field in cls._fields():
            if field.pk:
                return field
        return None

    @classmethod
    def _validate_class(cls, item: Model):
        if item is not cls:
            raise Exception(f"{item} must be of type {cls}")

    @classmethod
    def _field(cls, field_name: str) -> PormField:
        return cls._field_map()[field_name]

    #
    # Shortcuts
    #
    @classmethod
    def from_(cls) -> QueryBuilder:
        return Query.from_(cls.__tablename__)

    @classmethod
    def select(cls) -> QueryBuilder:
        return cls.from_().select("*")

    #
    # Queries
    #
    @classmethod
    async def insert_one(cls: Type[Model] | Table, /, item: Model) -> Model:

        cls._validate_class(item)

        query: QueryBuilder = (
            Query.into(cls.__tablename__)
            .columns(cls._fields(exclude_autogen=True))
            .insert(*cls._db_values(item, exclude_autogen=True))
        )
        return await Porm.fetch_one(with_returning(query), cls)

    @classmethod
    async def insert_many(cls: Type[Model] | Table, /, items: list[Model]) -> list[Model]:
        query: QueryBuilder = Query.info(cls.__tablename__).columns(*cls._fields())

        for item in items:
            cls._validate_class(item)
            query = query.insert(*cls._db_values(item))

        return await Porm.fetch_many(with_returning(query), cls)

    @classmethod
    async def fetch_first(
        cls: Type[Model] | Table, /, criterion: BasicCriterion, *, prefetch: list[Relationship] = []
    ) -> Optional[Model]:
        query: QueryBuilder = cls.select().where(criterion)
        query = query.limit(1)
        return await Porm.fetch_one(query.get_sql(), cls)

    @classmethod
    async def fetch_one(
        cls: Type[Model] | Table, /, criterion: BasicCriterion, *, prefetch: list[Relationship]
    ) -> Model:
        query: QueryBuilder = cls.select().where(criterion)
        query = query.limit(2)
        results = await Porm.fetch_many(query.get_sql(), cls)
        if len(results) > 1:
            raise Exception("Multiple objects were returned from get query")

        return results[0]

    @classmethod
    async def fetch_many(
        cls: Type[Model] | Table,
        /,
        criterion: BasicCriterion,
        *,
        prefetch: list[Relationship],
    ) -> list[Model]:
        query: QueryBuilder = cls.select().where(criterion)
        return await Porm.fetch_many(query.get_sql(), cls)

    @classmethod
    async def update_one(cls: Type[Model] | Table, /, item: Model) -> Model:

        cls._validate_class(item)

        query: QueryBuilder = Query.update(cls.__tablename__)

        for field in cls._fields():
            query = query.set(field.name, getattr(item, field.name))

        pk = cls._primary_key()

        query = query.where(pk == getattr(item, pk.name))

        return await Porm.fetch_one(with_returning(query), cls)

    @classmethod
    async def fetch_related(
        cls: Type[Model] | Table, /, items: list[Model], _relationships: tuple[tuple[Relationship]]
    ):

        [cls._validate_class(item) for item in items]

        # TODO: allow for single depth to not have to specify inside tuple
        for relationships in _relationships:
            relationship = relationships[0]

            sub_items = []

            if isinstance(relationship, ForeignKeyRelationship):
                foreign_keys = [getattr(item, relationship.self_field) for item in items]
                sub_items = await relationship.table.fetch_many(
                    relationship.table.select().where(
                        relationship.table._field(relationship.other_field).isin(foreign_keys)
                    )
                )

                sub_items = {getattr(i, relationship.other_field): i for i in sub_items}
                field_name = cls._relationship_field_name(relationship)

                for item in items:

                    foreign_key = getattr(item, relationship.self_field)

                    if foreign_key is None:
                        continue

                    setattr(item, field_name, sub_items[foreign_key])

                await cls.fetch_related(sub_items, relationships[1:])

            elif isinstance(relationship, ReverseRelationship):

                self_keys = [getattr(item, relationship.self_field) for item in items]

                sub_items = await relationship.table.fetch_many(
                    relationship.table.select().where(
                        relationship.table._field(relationship.other_field).isin(self_keys)
                    )
                )

                items = {getattr(i, relationship.self_field): i for i in items}
                field_name = cls._relationship_field_name(relationship)

                for sub_item in sub_items:
                    foreign_key = getattr(item, relationship.other_field)

                    item = items[foreign_key]

                    if getattr(item, field_name) is None:
                        setattr(item, field_name, [sub_item])
                    else:
                        getattr(item, field_name).append(sub_item)

                await cls.fetch_related(sub_items, relationships[1:])

            else:
                raise Exception("can only use ReverseRelationship and ForeignKeyRelationship")
