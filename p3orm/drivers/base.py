from __future__ import annotations

from typing import Type, TypeVar

from p3orm.table import Table

T = TypeVar("T", bound=Table)


class Driver:
    tables: list[Type[Table]]

    def __init__(self, tables: list[Type[Table]]) -> None:
        super().__init__()
        self.tables = tables
        for table in tables:
            table._init_stuff(self)
