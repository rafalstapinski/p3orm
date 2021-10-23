from typing import TypeVar

from pydantic import BaseModel

TableModel = type(BaseModel)
ModelFactory = TypeVar("ModelFactory", bound="BaseModel")
