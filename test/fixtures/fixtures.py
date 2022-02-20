import pytest
from pytest_postgresql import factories

from test.fixtures.helpers import create_base

postgresql_proc = factories.postgresql_proc(port=None, unixsocketdir="/var/run")
postgresql = factories.postgresql("postgresql_proc")
