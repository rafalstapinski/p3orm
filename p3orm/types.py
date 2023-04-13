from typing import Any, TypeVar

from pydantic import BaseModel

Model = TypeVar("Model", bound=BaseModel)

T = TypeVar("T", bound=Any)
