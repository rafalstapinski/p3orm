from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, NoReturn, Optional, Sequence, Type, Union, get_type_hints

from pydantic import BaseConfig, BaseModel
from pydantic.main import create_model
from pypika import Query
from pypika.queries import QueryBuilder
from pypika.terms import Criterion, Field

from p3orm.core import Porm
from p3orm.exceptions import (
    InvalidRelationship,
    MissingPrimaryKey,
    MissingRelationship,
    MissingTablename,
    MultipleResultsReturned,
    NoResultsReturned,
    UnloadedRelationship,
)
from p3orm.types import Model, T
from p3orm.utils import with_returning


class UNLOADED:
    def __getattribute__(self, name) -> NoReturn:
        if name == "__class__":
            return UNLOADED

        raise UnloadedRelationship("Relationship has not yet been loaded from the database")

    def __getitem__(*args) -> NoReturn:
        raise UnloadedRelationship("Relationship has not yet been loaded from the database")

    def __eq__(self, other):
        return isinstance(other, UNLOADED)

    def __repr__(self) -> str:
        return f"<UNLOADED RELATIONSHIP>"


class PormField(Field):
    pk: bool
    autogen: bool
    _type: Type

    def __init__(
        self,
        _type: Type,
        name: str,
        pk: Optional[bool] = False,
        autogen: Optional[bool] = False,
    ):
        self._type = _type
        self.name = name  # column name - must match field name as well
        self.pk = pk
        self.autogen = autogen


def Column(
    _type: Type[T],
    name: str,
    *,
    pk: Optional[bool] = False,
    autogen: Optional[bool] = False,
) -> Union[T, PormField]:
    return PormField(
        _type=_type,
        name=name,
        pk=pk,
        autogen=autogen,
    )


class _Relationship:

    self_field: str
    other_field: str

    def __init__(
        self,
        self_field: str,
        other_field: str,
    ):
        self.self_field = self_field
        self.other_field = other_field

    def __new__(cls, *args, **kwargs) -> _Relationship:
        if cls is _Relationship:
            raise InvalidRelationship(
                "Can not use Relationship directly. Must use ForeignKeyRelationship or ReverseRelationship"
            )

        return super().__new__(cls)


class ForeignKeyRelationship(_Relationship):
    ...


class ReverseRelationship(_Relationship):
    ...


class _TableModelConfig(BaseConfig):
    arbitrary_types_allowed = True


FetchType = Sequence[Sequence[_Relationship]]


class Table:

    __tablename__: str

    #
    # Magic
    #
    def __new__(cls: Union[Type[Model], Table], /, **_create_fields: Dict[str, Any]) -> Model:

        create_fields = deepcopy(_create_fields)

        for relationship_name in cls._relationship_map():
            create_fields[relationship_name] = UNLOADED()

        return cls._create_model_factory()(**create_fields)

    @classmethod
    def _create_model_factory(cls: Table) -> Type[Model]:

        factory_model_kwargs = {}
        for field_name, field in cls._field_map().items():
            factory_model_kwargs[field_name] = (field._type, None)

        for relationship_name in cls._relationship_map():
            factory_model_kwargs[relationship_name] = (UNLOADED, None)

        return create_model(cls.__name__, __config__=_TableModelConfig, **factory_model_kwargs)

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "__tablename__") or cls.__tablename__ is None:
            raise MissingTablename(f"{cls.__name__} must define a __tablename__ property")

        fields = cls._fields()

        if len([f for f in fields if f.pk]) != 1:
            raise MissingPrimaryKey(f"{cls.__name__} is missing a primary key")

    #
    # Introspective methods
    #
    @classmethod
    def _relationship_map(cls) -> Dict[str, _Relationship]:
        return {
            name: relationship for name in cls.__dict__ if isinstance(relationship := getattr(cls, name), _Relationship)
        }

    @classmethod
    def _relationship_field_name(cls, relationship: _Relationship) -> str:
        for field_name, _relationship in cls._relationship_map().items():
            if relationship == _relationship:
                return field_name

        raise MissingRelationship(f"Relationship {relationship} does not exist on {cls.__name__}")

    @classmethod
    def _fields(cls, exclude_autogen: Optional[bool] = False) -> List[PormField]:
        fields = [field for field_name in cls.__dict__ if isinstance(field := getattr(cls, field_name), PormField)]
        if exclude_autogen:
            fields = [f for f in fields if not f.autogen]
        return fields

    @classmethod
    def _field_map(cls, exclude_autogen: Optional[bool] = False) -> Dict[str, PormField]:
        fields = {
            field_name: field for field_name in cls.__dict__ if isinstance(field := getattr(cls, field_name), PormField)
        }
        return fields

    @classmethod
    def _db_values(cls, item: Model, exclude_autogen: Optional[bool] = False) -> List[Any]:
        return [getattr(item, field.name) for field in cls._fields(exclude_autogen=exclude_autogen)]

    @classmethod
    def _primary_key(cls) -> Optional[PormField]:
        for field in cls._fields():
            if field.pk:
                return field
        return None

    @classmethod
    def _field(cls, field_name: str) -> PormField:
        return cls._field_map()[field_name]

    #
    # Shortcuts
    #
    @classmethod
    def from_(cls) -> QueryBuilder:
        return QueryBuilder().from_(cls.__tablename__)

    @classmethod
    def select(cls, to_select: str = "*") -> QueryBuilder:
        return cls.from_().select(to_select)

    @classmethod
    def delete(cls) -> QueryBuilder:
        return QueryBuilder().delete().from_(cls.__tablename__)

    @classmethod
    def update(cls) -> QueryBuilder:
        return QueryBuilder().update(cls.__tablename__)

    #
    # Queries
    #
    @classmethod
    async def insert_one(
        cls: Union[Type[Model], Table],
        /,
        item: Model,
        *,
        prefetch: FetchType = None,
    ) -> Model:

        query: QueryBuilder = (
            Query.into(cls.__tablename__)
            .columns(cls._fields(exclude_autogen=True))
            .insert(*cls._db_values(item, exclude_autogen=True))
        )

        inserted: Optional[Model] = await Porm.fetch_one(with_returning(query), cls)

        if prefetch and inserted:
            [inserted] = await cls.fetch_related([inserted], prefetch)

        return inserted

    @classmethod
    async def insert_many(
        cls: Union[Type[Model], Table],
        /,
        items: List[Model],
        *,
        prefetch: FetchType = None,
    ) -> List[Model]:
        query: QueryBuilder = Query.into(cls.__tablename__).columns(*cls._fields(exclude_autogen=True))

        for item in items:
            query = query.insert(*cls._db_values(item, exclude_autogen=True))

        inserted = await Porm.fetch_many(with_returning(query), cls)

        if prefetch and inserted:
            inserted = await cls.fetch_related(inserted, prefetch)

        return inserted

    @classmethod
    async def fetch_first(
        cls: Union[Type[Model], Table],
        /,
        criterion: Criterion,
        *,
        prefetch: FetchType = None,
    ) -> Optional[Model]:
        query: QueryBuilder = cls.select().where(criterion)
        query = query.limit(1)

        result = await Porm.fetch_one(query.get_sql(), cls)

        if result and prefetch:
            [result] = await cls.fetch_related([result], prefetch)

        return result

    @classmethod
    async def fetch_one(
        cls: Union[Type[Model], Table],
        /,
        criterion: Criterion,
        *,
        prefetch: FetchType = None,
    ) -> Model:
        query: QueryBuilder = cls.select().where(criterion)
        query = query.limit(2)
        results = await Porm.fetch_many(query.get_sql(), cls)

        if len(results) > 1:
            raise MultipleResultsReturned(f"Multiple {cls.__name__} were returned when only one was expected")
        elif len(results) == 0:
            raise NoResultsReturned(f"No {cls.__name__} were returned when one was expected")

        result = results[0]

        if prefetch:
            [result] = await cls.fetch_related([result], prefetch)

        return result

    @classmethod
    async def fetch_all(
        cls: Union[Type[Model], Table],
        /,
        criterion: Criterion = None,
        *,
        prefetch: FetchType = None,
    ) -> List[Model]:

        query: QueryBuilder = cls.select()

        if criterion:
            query = query.where(criterion)

        results = await Porm.fetch_many(query.get_sql(), cls)

        if prefetch:
            results = await cls.fetch_related(results, prefetch)

        return results

    @classmethod
    async def update_one(
        cls: Union[Type[Model], Table],
        /,
        item: Model,
        *,
        prefetch: FetchType = None,
    ) -> Model:

        query: QueryBuilder = QueryBuilder().update(cls.__tablename__)

        for field in cls._fields():
            query = query.set(field.name, getattr(item, field.name))

        pk = cls._primary_key()

        query = query.where(pk == getattr(item, pk.name))

        updated = await Porm.fetch_one(with_returning(query), cls)

        if prefetch and updated:
            [updated] = await cls.fetch_related([updated], prefetch)

        return updated

    @classmethod
    async def delete_where(cls: Union[Type[Model], Table], /, criterion: Criterion) -> List[Model]:

        query: QueryBuilder = QueryBuilder().delete()
        query = query.from_(cls.__tablename__)
        query = query.where(criterion)
        return await Porm.fetch_many(with_returning(query), cls)

    @classmethod
    async def _load_relationships_for_items(
        cls: Union[Type[Model], Table],
        /,
        items: List[Union[Model, BaseModel]],
        _relationships: FetchType,
    ) -> List[Model]:
        """Loads relationships, updates items in place"""
        relationship_map = cls._relationship_map()
        type_hints = get_type_hints(cls)

        for relationships in _relationships:
            if not relationships:
                continue

            relationship = relationships[0]

            relationship_table: Type[Table] = None
            relationship_field_name: str = None
            for n, r in relationship_map.items():
                if r == relationship:
                    relationship_table = (
                        type_hints.get(n)
                        if isinstance(relationship, ForeignKeyRelationship)
                        else type_hints.get(n).__args__[0]
                    )

                    relationship_field_name = n

            if not relationship_table:
                raise InvalidRelationship(f"Relationship {relationship} doesn't exist on {cls}")

            keys = (
                [getattr(item, relationship.self_field) for item in items]
                if isinstance(relationship, ForeignKeyRelationship)
                else [getattr(item, relationship.self_field) for item in items]
            )

            sub_items_query: QueryBuilder = relationship_table.select().where(
                relationship_table._field(relationship.other_field).isin(keys)
            )

            sub_items = await Porm.fetch_many(sub_items_query.get_sql(), relationship_table)

            if isinstance(relationship, ForeignKeyRelationship):
                sub_items_map = {getattr(i, relationship.other_field): i for i in sub_items}

                for item in items:
                    foreign_key = getattr(item, relationship.self_field)

                    # Remove unloaded relationship as it has been fetched
                    if foreign_key is None:
                        setattr(item, relationship_field_name, None)
                        continue

                    setattr(item, relationship_field_name, sub_items_map[foreign_key])

            else:
                items_map = {getattr(i, relationship.self_field): i for i in items}

                # Attach all loaded sub_items to appropriate item
                for sub_item in sub_items:
                    foreign_key = getattr(sub_item, relationship.other_field)
                    item = items_map[foreign_key]

                    if isinstance(getattr(item, relationship_field_name), UNLOADED):
                        setattr(item, relationship_field_name, [sub_item])
                    else:
                        getattr(item, relationship_field_name).append(sub_item)

                # Remove UNLOADED relationships as they have now been loaded
                for item in items:
                    if isinstance(getattr(item, relationship_field_name), UNLOADED):
                        setattr(item, relationship_field_name, [])

            await relationship_table._load_relationships_for_items(sub_items, [relationships[1:]])

    @classmethod
    async def fetch_related(
        cls: Union[Type[Model], Table],
        /,
        items: List[Union[Model, BaseModel]],
        _relationships: FetchType,
    ) -> List[Model]:

        items = [i.copy() for i in items]
        await cls._load_relationships_for_items(items, _relationships)
        return items
