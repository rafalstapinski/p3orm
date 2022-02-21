from typing import Any, Dict, Optional

import asyncpg
from pypika.queries import QueryBuilder


def record_to_kwargs(record: asyncpg.Record) -> Dict[str, Any]:
    return {k: v for k, v in record.items()}


def with_returning(query: QueryBuilder, returning: Optional[str] = "*") -> str:
    return f"{query.get_sql()} RETURNING {returning}"
