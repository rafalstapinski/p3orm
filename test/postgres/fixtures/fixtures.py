from pytest_postgresql import factories

postgresql_proc = factories.postgresql_proc(port=None, unixsocketdir="/var/run")
postgresql = factories.postgresql("postgresql_proc")
