from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence, Type, Union, get_type_hints

from pydantic import BaseConfig, BaseModel
from pydantic.main import create_model
from pypika import Order, Query
from pypika.queries import QueryBuilder
from pypika.terms import Criterion, Parameter

from p3orm.core import dialect, driver, querybuilder
from p3orm.exceptions import (
    InvalidRelationship,
    MissingPrimaryKey,
    MissingRelationship,
    MissingTablename,
    MultiplePrimaryKeys,
    MultipleResultsReturned,
    NoResultsReturned,
)
from p3orm.fields import UNLOADED, RelationshipType, _PormField, _Relationship
from p3orm.types import Model
from p3orm.utils import is_optional, paramaterize, with_returning

FetchType = Sequence[Sequence[_Relationship]]


class Table:

    __tablename__: str

    class Meta:
        meta_table: bool = False

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
        class _TableModelConfig(BaseConfig):
            arbitrary_types_allowed = True
            allow_population_by_field_name = True
            fields = dict()

        factory_model_kwargs = {}
        for field_name, field in cls._field_map().items():
            field: _PormField

            default = ...
            if field.autogen or is_optional(field._type):
                default = None

            factory_model_kwargs[field_name] = (field._type, default)
            _TableModelConfig.fields[field_name] = field.column_name

        for relationship_name in cls._relationship_map():
            factory_model_kwargs[relationship_name] = (UNLOADED, None)

        return create_model(cls.__name__, __config__=_TableModelConfig, **factory_model_kwargs)

    def __init_subclass__(cls) -> None:
        if (not hasattr(cls, "__tablename__") or cls.__tablename__ is None) and cls.Meta.meta_table == False:
            raise MissingTablename(f"{cls.__name__} must define a __tablename__ property")

        fields = cls._fields()

        num_pkeys = len([f for f in fields if f.pk])
        if num_pkeys == 0:
            raise MissingPrimaryKey(f"{cls.__name__} must have 1 primary key field")

        elif num_pkeys > 1:
            raise MultiplePrimaryKeys(f"{cls.__name__} has more than 1 primary key field (check parent classes)")

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

        raise MissingRelationship(f"_Relationship {relationship} does not exist on {cls.__name__}")

    @classmethod
    def _fields(cls, exclude_autogen: Optional[bool] = False) -> List[_PormField]:
        fields: List[_PormField] = []
        for table in cls.__mro__:
            for field_name in table.__dict__:
                if isinstance(field := getattr(table, field_name), _PormField):
                    if field.column_name is None:
                        field.column_name = field_name
                        field.name = field_name
                    field.field_name = field_name
                    fields.append(field)

        if exclude_autogen:
            fields = [f for f in fields if not f.autogen]

        return fields

    @classmethod
    def _field_map(cls, exclude_autogen: Optional[bool] = False) -> Dict[str, _PormField]:
        fields = cls._fields(exclude_autogen)
        return {f.field_name: f for f in fields}

    @classmethod
    def _db_values(cls, item: Model, exclude_autogen: Optional[bool] = False) -> List[Any]:
        return [getattr(item, field.field_name) for field in cls._fields(exclude_autogen=exclude_autogen)]

    @classmethod
    def _primary_key(cls) -> Optional[_PormField]:
        for field in cls._fields():
            if field.pk:
                return field
        return None

    @classmethod
    def _field(cls, field_name: str) -> _PormField:
        return cls._field_map()[field_name]

    #
    # Shortcuts
    #
    @classmethod
    def from_(cls) -> QueryBuilder:
        return querybuilder().from_(cls.__tablename__)

    @classmethod
    def select(cls, to_select: str = "*") -> QueryBuilder:
        return cls.from_().select(to_select)

    @classmethod
    def delete(cls) -> QueryBuilder:
        return querybuilder().delete().from_(cls.__tablename__)

    @classmethod
    def update(cls) -> QueryBuilder:
        return querybuilder().update(cls.__tablename__)

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

        query: QueryBuilder = Query.into(cls.__tablename__).columns(cls._fields(exclude_autogen=True))

        query_args = cls._db_values(item, exclude_autogen=True)
        query_params = [Parameter(f"${i + 1}") for i in range(len(query_args))]

        query = query.insert(query_params)

        inserted: Optional[Model] = await driver().fetch_one(cls, with_returning(query), query_args)

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

        if not items:
            return []

        columns = cls._fields(exclude_autogen=True)
        columns_count = len(columns)
        query: QueryBuilder = Query.into(cls.__tablename__).columns(*columns)
        query_args: List[Any] = []

        for page, item in enumerate(items):
            query_args += cls._db_values(item, exclude_autogen=True)
            query_params = [Parameter(f"${page * columns_count + offset + 1}") for offset in range(columns_count)]
            query = query.insert(query_params)

        inserted = await driver().fetch_many(cls, with_returning(query), query_args)

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

        paramaterized_criterion, query_args = paramaterize(criterion, dialect=dialect())
        query: QueryBuilder = cls.select().where(paramaterized_criterion)
        query = query.limit(1)

        result = await driver().fetch_one(cls, query.get_sql(), query_args=query_args)

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

        paramaterized_criterion, query_args = paramaterize(criterion, dialect=dialect())

        query: QueryBuilder = cls.select().where(paramaterized_criterion)
        query = query.limit(2)

        results = await driver().fetch_many(cls, query.get_sql(), query_args)

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
        order: Union[_PormField, List[_PormField]] = None,
        by: Order = Order.asc,
        limit: int = None,
        prefetch: FetchType = None,
    ) -> List[Model]:

        query: QueryBuilder = cls.select()

        query_args = None
        if criterion:
            parameterized_criterion, query_args = paramaterize(criterion, dialect=dialect())
            query = query.where(parameterized_criterion)

        if order:
            order_fields = order if isinstance(order, list) else [order]
            query = query.orderby(*[o.column_name for o in order_fields], order=by)

        if limit:
            query = query.limit(limit)

        results = await driver().fetch_many(cls, query.get_sql(), query_args)

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

        query: QueryBuilder = querybuilder().update(cls.__tablename__)

        pk = cls._primary_key()
        parameterized_criterion, query_args = paramaterize(pk == getattr(item, pk.field_name), dialect=dialect())

        for i, field in enumerate(cls._fields()):
            field: _PormField
            query = query.set(field.column_name, Parameter(f"${i + 2}"))
            query_args.append(getattr(item, field.field_name))

        query = query.where(parameterized_criterion)

        updated = await driver().fetch_one(cls, with_returning(query), query_args)

        if prefetch and updated:
            [updated] = await cls.fetch_related([updated], prefetch)

        return updated

    @classmethod
    async def delete_where(cls: Union[Type[Model], Table], /, criterion: Criterion) -> List[Model]:

        query: QueryBuilder = querybuilder().delete()
        query = query.from_(cls.__tablename__)

        parameterized_criterion, query_args = paramaterize(criterion, dialect=dialect())

        query = query.where(parameterized_criterion)
        return await driver().fetch_many(cls, with_returning(query), query_args)

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
                        if relationship.relationship_type == RelationshipType.foreign_key
                        else type_hints.get(n).__args__[0]
                    )

                    relationship_field_name = n

            if not relationship_table:
                raise InvalidRelationship(f"Relationship {relationship} doesn't exist on {cls}")

            keys = (
                [getattr(item, relationship.self_column) for item in items]
                if relationship.relationship_type == RelationshipType.foreign_key
                else [getattr(item, relationship.self_column) for item in items]
            )

            paramaterized_criterion, query_args = paramaterize(
                relationship_table._field(relationship.foreign_column).isin(keys),
                dialect=dialect(),
            )
            sub_items_query: QueryBuilder = relationship_table.select().where(paramaterized_criterion)

            sub_items = await driver().fetch_many(relationship_table, sub_items_query.get_sql(), query_args)

            if relationship.relationship_type == RelationshipType.foreign_key:
                sub_items_map = {getattr(i, relationship.foreign_column): i for i in sub_items}

                for item in items:
                    foreign_key = getattr(item, relationship.self_column)

                    # Remove unloaded relationship as it has been fetched
                    if foreign_key is None:
                        setattr(item, relationship_field_name, None)
                        continue

                    setattr(item, relationship_field_name, sub_items_map[foreign_key])

            else:
                items_map = {getattr(i, relationship.self_column): i for i in items}

                # Attach all loaded sub_items to appropriate item
                for sub_item in sub_items:
                    foreign_key = getattr(sub_item, relationship.foreign_column)
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
