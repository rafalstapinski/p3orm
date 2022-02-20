from __future__ import annotations

from typing import TYPE_CHECKING

from pytest import param

from p3orm.core import Porm

if TYPE_CHECKING:
    from psycopg2 import connection

from test.fixtures.queries import BASE_DATA, BASE_TABLES


def create_base_tables(postgresql: connection):

    cursor = postgresql.cursor()
    cursor.execute(BASE_TABLES)
    postgresql.commit()
    cursor.close()


def create_base_data(postgresql: connection):

    cursor = postgresql.cursor()
    cursor.execute(BASE_DATA)
    postgresql.commit()
    cursor.close()


def create_base(postgresql: connection):
    create_base_tables(postgresql)
    create_base_data(postgresql)
