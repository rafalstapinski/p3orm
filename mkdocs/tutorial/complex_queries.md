# Complex queries

p3orm has full support for executing <a href="https://github.com/kayak/pypika">PyPika</a> queries. PyPika queries are constructed by building blocks that are analogous to the underlying SQL, the learning curve is minimal if you already know SQL.

### Available PyPika shortcuts
- `select` - Equivalent to PyPika's `QueryBuilder().from_(tablename).select(field)`. This defaults field to return everything `*` but you can pass in a specific `_PormField` for executing subqueries.
- `update` - Equivalent to PyPika's `QueryBuilder().update(tablename)`. You can then chain this with your own `.where()` and `.set()` statements.
- `delete` - Equivalent to PyPika's `QueryBuilder().delete().from(tablename)`. You can then chain this with your own `.where()` statement. 
- `from_` -> Calls underlying` QueryBuilder().from_(tablename)`, useful if you need to execute broader queries.

### Selecting with PyPika queries

```python
subquery = OtherThing.select("thing_id").where(OtherThing.id == 1)
query = Thing.select().where(Thing.id.isin(subquery))

things = await Thing.execute_many(query)
```

### Updating with PyPika queries

```python
from p3orm import with_returning

query = Thing.update().where(Thing.name == "name").set(Thing.name, "another name")

updated_things = await Thing.execute_many(with_returning(query))
```

### Deleting with PyPika queries

```python
from p3orm.utils import with_returning

subquery = OtherThing.from_().select("thing_id").where(OtherThing.id == 1)
query = Thing.delete().where(Thing.id.isin(subquery))

deleted_things = await Thing.execute_many(with_returning(query))
```
