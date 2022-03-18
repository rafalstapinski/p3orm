from typing import Any, Dict, List, Optional, Tuple, Type, Union, get_args, get_origin

import asyncpg
from pypika.queries import QueryBuilder
from pypika.terms import BasicCriterion, ContainsCriterion, Criterion, Equality, NullValue, Parameter, RangeCriterion


def record_to_kwargs(record: asyncpg.Record) -> Dict[str, Any]:
    return {k: v for k, v in record.items()}


def with_returning(query: QueryBuilder, returning: Optional[str] = "*") -> str:
    return f"{query.get_sql()} RETURNING {returning}"


def paramaterize(criterion: Criterion, query_args: List[Any] = None) -> Tuple[Criterion, List[Any]]:

    if query_args == None:
        query_args = []

    param_start_index = max(len(query_args), 1)

    if isinstance(criterion, BasicCriterion):
        param = Parameter(f"${param_start_index}")
        query_args.append(criterion.right.value)
        return BasicCriterion(criterion.comparator, criterion.left, param, criterion.alias), query_args

    elif isinstance(criterion, ContainsCriterion):
        param = Parameter(f"ANY (${param_start_index})")
        query_args.append([i.value for i in criterion.container.values if not isinstance(i, NullValue)])
        return BasicCriterion(Equality.eq, criterion.term, param, criterion.alias), query_args

    elif isinstance(criterion, RangeCriterion):
        start_param = Parameter(f"${param_start_index}")
        end_param = Parameter(f"${param_start_index + 1}")

        query_args += [criterion.start.value, criterion.end.value]
        # There are several RangeCriterion, create a new one with the same subclass
        return criterion.__class__(criterion.term, start_param, end_param, criterion.alias), query_args

    return criterion, query_args


def is_optional(_type: Type):
    return get_origin(_type) is Union and type(None) in get_args(_type)
