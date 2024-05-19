from enum import Enum
from types import NoneType, UnionType
from typing import Any, Type, cast, get_args, get_origin

import asyncpg
from pypika import Criterion, NullValue, Parameter
from pypika.enums import Comparator
from pypika.queries import QueryBuilder
from pypika.terms import BasicCriterion, ComplexCriterion, ContainsCriterion, RangeCriterion, ValueWrapper

try:
    from pydantic import BaseModel

    PydanticBaseModel = BaseModel
except ImportError:
    PydanticBaseModel = None

from p3orm.fields import PormField


def is_optional(t: Type) -> bool:
    return get_origin(t) == UnionType and NoneType in get_args(t)


def get_base_type(t: Type) -> Type:
    if is_optional(t):
        return get_args(t)[0]
    return t


def is_field_pydantic(field: PormField) -> bool:
    base_type = get_base_type(field._data_type)

    try:
        return bool(PydanticBaseModel) and issubclass(base_type, PydanticBaseModel)
    except:  # noqa
        ...

    return False


def is_field_enum(field: PormField) -> bool:
    base_type = get_base_type(field._data_type)

    if isinstance(base_type, type(Enum)):
        return issubclass(base_type, Enum)

    if get_origin(base_type) == UnionType:
        return all(issubclass(i, Enum) for i in get_args(base_type))

    return False


def cast_enum(field: PormField, value: str) -> bool:
    base_type = get_base_type(field._data_type)

    if isinstance(base_type, type(Enum)):
        return base_type(value)

    if get_origin(base_type) == UnionType:
        for i in get_args(base_type):
            try:
                return i(value)
            except:  # noqa
                ...

    raise ValueError(f"Could not cast {value} to {base_type}")


class PormComparator(Comparator):
    empty = " "
    in_ = " IN "


def _param(index: int) -> Parameter:
    return Parameter(f"${index}")


def record_to_kwargs(record: asyncpg.Record) -> dict[str, Any]:
    return {k: v for k, v in record.items()}


def with_returning(query: QueryBuilder, returning: str = "*") -> str:
    return f"{query.get_sql()} RETURNING {returning}"


def _parameterize(criterion: Criterion, query_args: list[Any], param_index: int = 0) -> tuple[Criterion, list[Any]]:
    if isinstance(criterion, ComplexCriterion):
        left, query_args = _parameterize(cast(Criterion, criterion.left), query_args, param_index)
        right, query_args = _parameterize(cast(Criterion, criterion.right), query_args, param_index + len(query_args))
        return ComplexCriterion(criterion.comparator, left, right, criterion.alias), query_args

    elif isinstance(criterion, BasicCriterion):
        query_args.append(cast(ValueWrapper, criterion.right).value)
        param_index += 1
        return (
            BasicCriterion(
                criterion.comparator,
                criterion.left,
                _param(param_index),
                criterion.alias,
            ),
            query_args,
        )

    elif isinstance(criterion, ContainsCriterion):
        criterion_args = [i.value if not isinstance(i, NullValue) else None for i in criterion.container.values]
        query_args += criterion_args
        params = []
        for _ in range(len(criterion_args)):
            param_index += 1
            params.append(f"${param_index}")
        return (
            BasicCriterion(
                PormComparator.in_,
                criterion.term,
                Parameter(f"""({", ".join(params)})"""),
                criterion.alias,
            ),
            query_args,
        )

    elif isinstance(criterion, RangeCriterion):
        query_args += [criterion.start.value, criterion.end.value]
        param_index += 1
        start_param = _param(param_index)
        param_index += 1
        end_param = _param(param_index)
        # There are several RangeCriterion, create a new one with the same subclass
        return criterion.__class__(criterion.term, start_param, end_param, criterion.alias), query_args

    return criterion, query_args


def parameterize[T](criterion: Criterion, query_args: list[T] | None = None) -> tuple[Criterion, list[T]]:
    if query_args is None:
        query_args = []

    return _parameterize(criterion, query_args)
