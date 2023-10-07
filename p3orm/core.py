from __future__ import annotations

from typing import TYPE_CHECKING

from pypika.enums import Dialects
from pypika.queries import QueryBuilder

from p3orm.drivers.base import BaseDriver
from p3orm.exceptions import NotConnected

if TYPE_CHECKING:
    from p3orm.drivers.postgres import PostgresDriver
    from p3orm.drivers.sqlite import SqliteDriver

DRIVER: BaseDriver = None
DIALECT: Dialects = None


def postgres() -> PostgresDriver:
    from p3orm.drivers.postgres import PostgresDriver

    global DRIVER, DIALECT
    if DRIVER:
        return DRIVER
    DRIVER = PostgresDriver()
    DIALECT = Dialects.POSTGRESQL
    return DRIVER


def sqlite() -> SqliteDriver:
    from p3orm.drivers.sqlite import SqliteDriver
    from p3orm.utils import validate_sqlite_version

    global DRIVER, DIALECT
    if DRIVER:
        return DRIVER
    validate_sqlite_version()
    DRIVER = SqliteDriver()
    DIALECT = Dialects.SQLLITE
    return DRIVER


def querybuilder() -> QueryBuilder:
    return QueryBuilder(dialect=DIALECT)


def driver() -> BaseDriver:
    global DRIVER
    if DRIVER:
        return DRIVER
    else:
        raise NotConnected("No driver as not connected")


def dialect() -> Dialects:
    global DIALECT
    if DIALECT:
        return DIALECT
    else:
        raise NotConnected("No dialect as not connected")
