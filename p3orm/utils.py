from types import NoneType, UnionType
from typing import Any, Optional, Type, Union, cast, get_args, get_origin

import asyncpg
from pypika import Criterion, NullValue, Parameter
from pypika.enums import Comparator
from pypika.queries import QueryBuilder
from pypika.terms import BasicCriterion, ComplexCriterion, ContainsCriterion, RangeCriterion, ValueWrapper


def is_optional(t: Type) -> bool:
    return get_origin(t) == UnionType and NoneType in get_args(t)


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
