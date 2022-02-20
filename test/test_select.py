from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from p3orm.core import Porm

from test.fixtures.helpers import create_base, create_base_and_connect
from test.fixtures.tables import Company, Employee, OrgChart

if TYPE_CHECKING:
    from psycopg2 import connection


@pytest.mark.asyncio
async def test_select(postgresql: connection):

    await create_base_and_connect(postgresql)
