from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union, get_args, get_origin

if TYPE_CHECKING:
    import asyncpg

from pypika.queries import QueryBuilder
from pypika.terms import (
    BasicCriterion,
    Comparator,
    ComplexCriterion,
    ContainsCriterion,
    Criterion,
    NullValue,
    Parameter,
    RangeCriterion,
)

from p3orm.exceptions import InvalidSQLiteVersion


class PormComparator(Comparator):
    empty = " "
    in_ = " IN "


def record_to_kwargs(record: asyncpg.Record) -> Dict[str, Any]:
    return {k: v for k, v in record.items()}


def with_returning(query: QueryBuilder, returning: Optional[str] = "*") -> str:
    return f"{query.get_sql()} RETURNING {returning}"


def _param(index: int) -> Parameter:
    # if dialect() == Dialects.SQLLITE:
    #     return Parameter("?")
    # else:
    #     return Parameter(f"${index}")
    return Parameter(f"${index}")


def _parameterize(criterion: Criterion, query_args: List[Any], param_index: int = 0) -> Tuple[Criterion, List[Any]]:
    if isinstance(criterion, ComplexCriterion):
        left, query_args = _parameterize(criterion.left, query_args, param_index)
        right, query_args = _parameterize(criterion.right, query_args, param_index + len(query_args))
        return ComplexCriterion(criterion.comparator, left, right, criterion.alias), query_args

    elif isinstance(criterion, BasicCriterion):
        query_args.append(criterion.right.value)
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
        for i in range(len(criterion_args)):
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


def paramaterize(
    criterion: Criterion,
    query_args: List[Any] = None,
) -> Tuple[Criterion, List[Any]]:
    if query_args == None:
        query_args = []

    return _parameterize(criterion, query_args)


def is_optional(_type: Type):
    return get_origin(_type) is Union and type(None) in get_args(_type)


def validate_sqlite_version():
    if sqlite3.sqlite_version_info < (3, 35, 0):
        raise InvalidSQLiteVersion("p3orm requires SQLite engine version 3.35 or higher")
