# p3orm

<a href="https://rafalstapinski.github.io/p3orm">
  <img src="https://rafalstapinski.github.io/p3orm/img/logo.svg" alt="p3orm logo" />
</a>

<p align="center">
  <strong>
    <em>
      Utilitarian Python ORM for Postgres, backed by <a href="https://github.com/MagicStack/asyncpg">asyncpg</a>, <a href="https://github.com/samuelcolvin/pydantic">Pydantic</a>, and <a href="https://github.com/kayak/pypika">PyPika</a>
    </em>
  </strong>
</p>

<p align="center">
  <a href="https://github.com/rafalstapinski/porm/actions/workflows/test.yml" target="_blank">
    <img src="https://github.com/rafalstapinski/porm/actions/workflows/test.yml/badge.svg" alt="Test Status" />
  </a>
  <a href="https://pypi.org/project/p3orm" target="_blank">
    <img src="https://img.shields.io/pypi/v/p3orm?color=%2334D058" alt="pypi" />
  </a>
  <a href="https://pypi.org/project/p3orm" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/p3orm?color=%23334D058" alt="Supported Python Versions: 3.8, 3.9, 3.10" />
  </a>
  <a href="https://github.com/rafalstapinski/p3orm/blob/master/LICENSE" target="_blank">
    <img src="https://img.shields.io/pypi/l/p3orm?color=%23334D058" alt="MIT License" />
  </a>
</p>

<h2>Philosophy</h2>

90% of the time we talk to a database is with a CRUD operation. p3orm provides convenience helpers for fetching (one, first, many), inserting (one, many), updating (one), and deleting (one, many).

The remaining 10% is a bit more complicated. p3orm doesn't attempt to hide SQL queries or database interactions behind any magic. Instead, it empowers you to write direct and legible SQL queries with [PyPika](https://github.com/kayak/pypika) and execute them explicitly against the database.


### Objects created or fetched by p3orm are dead, they're just [Pydantic](https://github.com/samuelcolvin/pydantic) models. If you want to interact with the database, you do so explicitly.

<h2>Features</h2>

- Comprehensive type annotations (full intellisense support)
- Type validation
- Full support for PyPika queries
- Support for all `asyncpg` [types](https://magicstack.github.io/asyncpg/current/usage.html#type-conversion)

<h2>Installation</h2>

Install with `poetry`
```sh
poetry add p3orm
```

or with `pip`

```sh
pip install p3orm
```

<h2>Basic Usage</h2>

```python

from datetime import datetime

from p3orm.core import Porm
from p3orm.table import Table, PormField

class Thing(Table):
    id = PormField(int, "id", pk=True, autogen=True)
    name = PormField(str, "name")
    created_at = PormField(datetime, "created_at", autogen=True)

await Porm.connect(user=..., password=..., database=..., host=..., port=...)

thing = Thing(name="Name")

inserted = await Thing.insert_one(thing)

fetched = await Thing.fetch_first(Thing.id == 1)

fetched.name = "Changed"

updated = await Thing.update_one(fetched)

deleted = await Thing.delete_where(Thing.id == updated.id)
```

<h2>Usage</h2>

See <a href="https://rafalstapinski.github.io/p3orm">docs</a>
