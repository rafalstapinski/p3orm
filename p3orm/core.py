from pypika.enums import Dialects
from pypika.queries import QueryBuilder

from p3orm.drivers.base import BaseDriver
from p3orm.drivers.postgres import PostgresDriver
from p3orm.drivers.sqlite import SqliteDriver
from p3orm.exceptions import NotConnected

_DRIVER: BaseDriver = None
_DIALECT: Dialects = None


def postgres() -> PostgresDriver:
    global _DRIVER, _DIALECT
    if _DRIVER:
        return _DRIVER
    _DRIVER = PostgresDriver()
    _DIALECT = Dialects.POSTGRESQL
    return _DRIVER


def sqlite() -> SqliteDriver:
    global _DRIVER, _DIALECT
    if _DRIVER:
        return _DRIVER
    _DRIVER = SqliteDriver()
    _DIALECT = Dialects.SQLLITE
    return _DRIVER


def querybuilder() -> QueryBuilder:
    return QueryBuilder(dialect=_DIALECT)


def driver() -> BaseDriver:
    global _DRIVER
    if _DRIVER:
        return _DRIVER
    else:
        raise NotConnected("No database connection exists")
