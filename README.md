# p3orm

<a href="https://rafalstapinski.github.io/p3orm">
  <img src="https://rafalstapinski.github.io/p3orm/img/logo.svg" alt="p3orm logo" />
</a>

<p align="center">
  <strong>
    <em>
      Utilitarian Python ORM for Postgres/SQLite powered by <a href="https://github.com/MagicStack/asyncpg">asyncpg</a>/<a href="https://github.com/omnilib/aiosqlite">aiosqlite</a>, <a href="https://github.com/samuelcolvin/pydantic">Pydantic</a>, and <a href="https://github.com/kayak/pypika">PyPika</a>
    </em>
  </strong>
</p>

---

**Documentation**: <a href="https://rafalstapinski.github.io/p3orm">https://rafalstapinski.github.io/p3orm</a>

**Source Code**: <a href="https://github.com/rafalstapinski/p3orm">https://github.com/rafalstapinski/p3orm</a>

---

<p align="center">
  <a href="https://github.com/rafalstapinski/p3orm/actions/workflows/test.yml" target="_blank">
    <img src="https://github.com/rafalstapinski/p3orm/actions/workflows/test.yml/badge.svg" alt="Test Status" />
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

---
<h2>Philosophy</h2>

90% of the time we talk to a database is with a CRUD operation. p3orm provides convenience helpers for fetching (one, first, many), inserting (one, many), updating (one), and deleting (one, many).

The remaining 10% is a bit more complicated. p3orm doesn't attempt to hide SQL queries or database interactions behind any magic. Instead, it empowers you to write direct and legible SQL queries with [PyPika](https://github.com/kayak/pypika) and execute them explicitly against the database.

Notably, objects created or fetched by p3orm are dead, they're just [Pydantic](https://github.com/samuelcolvin/pydantic) models. If you want to interact with the database, you do so explicitly.

### tl;dr - p3orm makes easy things easy, and hard things possible

---
<h2>Features</h2>

- Comprehensive type annotations (full intellisense support)
- String type validation an parsing powered by `Pydantic`
- Support for `PyPika` queries
- Support for all `postgres` [datatypes](https://magicstack.github.io/asyncpg/current/usage.html#type-conversion)
- Support for all `sqlite` [datatypes](https://www.sqlite.org/datatype3.html)

---
<h2>Installation</h2>

Install with `poetry`
```sh
poetry add p3orm[sqlite]
# or
poetry add p3orm[postgres]
```

or with `pip`

```sh
pip install p3orm[sqlite]
# or
pip install p3orm[postgres]
```

The `[sqlite]` extra installs `aiosqlite` as p3orm's database driver, whereas `[postgres]` installs `asyncpg`.

---
<h2>Basic Usage</h2>

```python
from datetime import datetime
from p3orm import Column, Table

from p3orm import sqlite as db
# or: from p3orm import postgres as db

class Thing(Table):
    id = Column(int, pk=True, autogen=True)
    name = Column(str)
    created_at = Column(datetime, autogen=True)

await db().connect(":memory:")

thing = Thing(name="Name")

inserted = await Thing.insert_one(thing)

fetched = await Thing.fetch_first(Thing.id == 1)

fetched.name = "Changed"

updated = await Thing.update_one(fetched)

deleted = await Thing.delete_where(Thing.id == updated.id)

await db().disconnect()
```
