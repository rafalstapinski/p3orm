# p<sup>3</sup>orm

![Test](https://github.com/rafalstapinski/porm/actions/workflows/test.yml/badge.svg)

Minimal PostgreSQL Python ORM, backed by [asyncpg](https://github.com/MagicStack/asyncpg), [Pydantic](https://github.com/samuelcolvin/pydantic), and [PyPika](https://github.com/kayak/pypika). 

## Philosophy

90% of the time we talk to a database is with a CRUD operation. p<sup>3</sup>orm provides helpers

The remaining 10% is a bit more complicated. p<sup>3</sup>orm doesn't attempt to hide SQL queries behind any magic, instead it empowers you to write direct, explicit, and legible SQL queries with [PyPika](https://github.com/kayak/pypika).

Object created or fetched by p<sup>3</sup>orm are **dead**, they're just Pydantic models. If you want to manipulate the database, you do so explicitly.


## Roadmap

- [x] Annotation type definition
- [x] Relationships
- [x] Tests
- [ ] Pool
- [ ] Filter annotations when class and when instance
