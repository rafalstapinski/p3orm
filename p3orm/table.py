from __future__ import annotations

import sys
from copy import deepcopy
from typing import Any, Callable, Dict, Generator, List, Sequence, Type, Union, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo
from pydantic.main import create_model
from pypika import Order, Query
from pypika.queries import QueryBuilder
from pypika.terms import Criterion, Parameter

from p3orm.core import driver, querybuilder
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

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

FetchType = Sequence[Sequence[_Relationship]]


class TableInstance(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        frozen=False,
    )

    __pydantic_complete__ = False

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BaseModel):
            return (
                self.__dict__ == other.__dict__
                and self.__pydantic_private__ == other.__pydantic_private__
                and self.__pydantic_extra__ == other.__pydantic_extra__
            )
        else:
            return NotImplemented  # delegate to the other item in the comparison


class Table:
    # class Table:
    __tablename__: str

    class Meta:
        meta_table: bool = False

    _model_factory: type[BaseModel]

    #
    # Magic
    #
    def __new__(cls: Union[Type[Model], Table], /, **_create_fields: Dict[str, Any]) -> Model:
        create_fields = deepcopy(_create_fields)

        for relationship_name in cls._relationship_map():
            create_fields[relationship_name] = UNLOADED()

        return cls._create_model_factory()(**create_fields)

    @classmethod
    def _create_model_factory(cls: Type[Table]) -> Type[BaseModel]:
        if hasattr(cls, "_model_factory") and cls._model_factory:
            return cls._model_factory

        class _TableInstance(TableInstance):
            ...

        factory_model_kwargs = {}
        for field_name, field in cls._field_map().items():
            field: _PormField

            default = ...
            if field.autogen or is_optional(field._type):
                default = None

            factory_model_kwargs[field_name] = (field._type, Field(default, alias=field.column_name))

        for relationship_name in cls._relationship_map():
            factory_model_kwargs[relationship_name] = (UNLOADED, None)

        factory = create_model(cls.__name__, __base__=_TableInstance, **factory_model_kwargs)
        cls._model_factory = factory
        return cls._model_factory

    def __init_subclass__(cls: Type[Table]) -> None:
        # raise if concrete table without tablename
        if (not hasattr(cls, "__tablename__") or cls.__tablename__ is None) and cls.Meta.meta_table == False:
            raise MissingTablename(f"{cls.__name__} must define a __tablename__ property")

        # don't calculate for meta tables
        elif cls.Meta.meta_table and not hasattr(cls, "__tablename__"):
            return

        fields = cls._fields()

        num_pkeys = len([f for f in fields if f.pk])
        if num_pkeys == 0:
            raise MissingPrimaryKey(f"{cls.__name__} must have 1 primary key field")

        elif num_pkeys > 1:
            raise MultiplePrimaryKeys(f"{cls.__name__} has more than 1 primary key field (check parent classes)")

        cls._create_model_factory()

    @classmethod
    def __get_validators__(cls) -> Generator[Callable, None, None]:
        yield cls.__validate

    @classmethod
    def __validate(cls, v: Model | Any, _: ValidationInfo) -> Model:
        assert cls.__name__ == v.__class__.__name__, f"must be a valid {cls.__name__}"
        return v

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
    def _fields(cls, exclude_autogen: bool | None = False) -> List[_PormField]:
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
    def _field_map(cls, exclude_autogen: bool | None = False) -> Dict[str, _PormField]:
        fields = cls._fields(exclude_autogen)
        return {f.field_name: f for f in fields}

    @classmethod
    def _db_values(cls, item: Self, exclude_autogen: bool | None = False) -> List[Any]:
        return [getattr(item, field.field_name) for field in cls._fields(exclude_autogen=exclude_autogen)]

    @classmethod
    def _primary_key(cls) -> _PormField | None:
        for field in cls._fields():
            if field.pk:
                return field
        return None

    @classmethod
    def _field(cls, field_name: str) -> _PormField:
        return cls._field_map()[field_name]

    @classmethod
    def is_type(cls, obj: Any) -> bool:
        return obj.__class__ == cls._model_factory

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
        cls: Type[Self] | Table,
        /,
        item: Model,
        *,
        prefetch: FetchType = None,
    ) -> Self:
        query: QueryBuilder = Query.into(cls.__tablename__).columns(cls._fields(exclude_autogen=True))

        query_args = cls._db_values(item, exclude_autogen=True)
        query_params = [Parameter(f"${i + 1}") for i in range(len(query_args))]

        query = query.insert(query_params)

        inserted: Self | None = await driver().fetch_one(cls, with_returning(query), query_args)

        if prefetch and inserted:
            [inserted] = await cls.fetch_related([inserted], prefetch)

        return inserted

    @classmethod
    async def insert_many(
        cls: Type[Self] | Table,
        /,
        items: List[Self],
        *,
        prefetch: FetchType = None,
    ) -> List[Self]:
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
        cls: Type[Self] | Table,
        /,
        criterion: Criterion,
        *,
        prefetch: FetchType = None,
    ) -> Self | None:
        paramaterized_criterion, query_args = paramaterize(criterion)
        query: QueryBuilder = cls.select().where(paramaterized_criterion)
        query = query.limit(1)

        result = await driver().fetch_one(cls, query.get_sql(), query_args=query_args)

        if result and prefetch:
            [result] = await cls.fetch_related([result], prefetch)

        return result

    @classmethod
    async def fetch_one(
        cls: Type[Self] | Table,
        /,
        criterion: Criterion,
        *,
        prefetch: FetchType = None,
    ) -> Self:
        paramaterized_criterion, query_args = paramaterize(criterion)

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
        cls: Type[Self] | Table,
        /,
        criterion: Criterion = None,
        *,
        order: Union[_PormField, List[_PormField]] = None,
        by: Order = Order.asc,
        limit: int = None,
        prefetch: FetchType = None,
    ) -> List[Self]:
        query: QueryBuilder = cls.select()

        query_args = None
        if criterion:
            parameterized_criterion, query_args = paramaterize(criterion)
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
        cls: Type[Self] | Table,
        /,
        item: Self,
        *,
        prefetch: FetchType = None,
    ) -> Self:
        query: QueryBuilder = querybuilder().update(cls.__tablename__)

        pk = cls._primary_key()
        parameterized_criterion, query_args = paramaterize(pk == getattr(item, pk.field_name))

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
    async def delete_where(cls: Type[Self] | Table, /, criterion: Criterion) -> List[Self]:
        query: QueryBuilder = querybuilder().delete()
        query = query.from_(cls.__tablename__)

        parameterized_criterion, query_args = paramaterize(criterion)

        query = query.where(parameterized_criterion)
        return await driver().fetch_many(cls, with_returning(query), query_args)

    @classmethod
    async def _load_relationships_for_items(
        cls: Type[Self] | Table,
        /,
        items: List[Union[Model, BaseModel]],
        _relationships: FetchType,
    ):
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
        cls: Type[Self] | Table,
        /,
        items: List[Union[Model, BaseModel]],
        _relationships: FetchType,
    ) -> List[Self]:
        items = [i.model_copy() for i in items]
        await cls._load_relationships_for_items(items, _relationships)
        return items
