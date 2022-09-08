# Connecting to a Postgres database

p3orm allows you to connect either with a direct connection or with a connection pool. You can only connect with one of these at a time on a single instance. If you attempt to establish a new connection or pool while one already exists, p3orm will raise a `p3orm.exceptions.AlreadyConnected` exception.

## Regular connections

With p3orm you can open a single connection to the database. This is useful for simpler short lived applications like a script. You can open a connection by using the `PostgresDriver.connect` method.

```python
from p3orm import postgres

await postgres().connect(dsn=...)

# or

await postgres().connect(user=..., password=..., database=..., host=..., port=...)
```

This will create an underlying `asyncpg.Connection` which is available for inspection as a property on your instance as `postgres().connection`. You can also pass <a href="https://magicstack.github.io/asyncpg/current/api/index.html#connection" >keyword arguments</a> directly down into the `asyncpg.connect` method.

## Connection pooling

For many applications like web servers, it's advisable to use a <a href="https://stackoverflow.blog/2020/10/14/improve-database-performance-with-connection-pooling/" >connection pool</a>.

```python
from p3orm import postgres

await postgres().connect_pool(dsn=...)

# or

await postgres().connect_pool(user=..., password=..., database=..., host=..., port=...)
```

This will create an underlying `asyncpg.Pool` which is available for inspection as a property on your instance as `postgres().pool`. You can also pass <a href="https://magicstack.github.io/asyncpg/current/api/index.html#connection-pools">keyword arguments</a> directly down into the `asyncpg.create_pool` method. Some of these configuration options that are typically modified include `min_size`, `max_size`, and `max_inactive_connection_lifetime` which can be tuned to affect the performance of your application.

## Disconnecting

```python
await postgres().disconnect()
```

This method will close the existing `asyncpg.Connection` or `asyncpg.Pool` and remove it from the instance.
