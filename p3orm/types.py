from typing import Any, TypeVar

from pydantic import BaseModel

TableModel = type(BaseModel)
Model = TypeVar("Model", bound=TableModel)

Annotation = TypeVar("Annotation", bound=Any)
