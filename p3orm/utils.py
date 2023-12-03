from types import NoneType, UnionType
from typing import Optional, Type, Union, get_args, get_origin


def is_optional(t: Type) -> bool:
    return get_origin(t) == UnionType and NoneType in get_args(t)
