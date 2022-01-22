# porm

Minimal PostgreSQL Python ORM, backed by [asyncpg](https://github.com/MagicStack/asyncpg), [Pydantic](https://github.com/samuelcolvin/pydantic), and [PyPika](https://github.com/kayak/pypika). 

## Philosophy

90% of the time we talk to a database is with a CRUD operation. porm provides helpers

The remaining 10% is a bit more complicated. porm doesn't attempt to hide SQL queries behind any magic, instead it empowers you to write direct, explicit, and legible SQL queries with [PyPika](https://github.com/kayak/pypika).

Object created or fetched by porm are **dead**, they're just (currently) Pydantic models. If you want to manipulate the database, you do so explicitly.


## Roadmap

- [ ] Annotation type definition
- [ ] Relationships
- [ ] Tests
- [ ] Look into [attrs](https://github.com/python-attrs/attrs) over pydantic (does this actually need type *validation*)
