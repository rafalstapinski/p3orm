from typing import TYPE_CHECKING, TypeVar, Union

from pydantic import BaseModel

TableModel = type(BaseModel)
# ModelFactory = TypeVar("ModelFactory", bound="BaseModel")
Model = TypeVar("Model", bound=TableModel)
