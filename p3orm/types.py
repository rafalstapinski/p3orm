from typing import Any, TypeVar

from pydantic import BaseModel

TableModel = type(BaseModel)
Model = TypeVar("Model", bound=TableModel)

T = TypeVar("T", bound=Any)
