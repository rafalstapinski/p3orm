# Relationships

p3orm supports two types of relationships

- `ForeignKeyRelationship` - Analogous to the table having a foreign key. This will always retrieve a single referenced model.
- `ReverseRelationship` - Analagous to a different table having a foreign key referencing the current table. This will always retrieve a list of referenced models.

## Default behavior

By default, relationships are not loaded from the database. Instead, all relationship fields are instantiated with the `p3orm.table.UNLOADED` object. This object will raise a `p3orm.exceptions.UnloadedRelationship` exception if you try to access any property on it.

## Usage

```python
from __future__ import annotations

from p3orm.table import Table, ForeignKeyRelationship, ReverseRelationship, PormField

class Parent(Table):
  id = PormField(int, "id", pk=True, autogen=True)

  children: list[Child] = ReverseRelationship(self_field="id", other_field="parent_id")

class Child(Table):
  id = PormField(int, "id", pk=True, autogen=True)
  name = PormField(str, "name")
  parent_id = PormField(int, "parent_id")

  parent: Parent = ForeignKeyRelationship(self_field="parent_id", other_field="id")
```

It's not necessary to import `from future import __annotations__`. If you don't import, just know you will have to mark your anotations as strings, e.g. `children: list["Child"]` or `parent: "Parent"`

### Fetching foreign key relationships
```python
child = await Child.fetch_one(Child.id == 1)

child.parent # <p3orm.table.UNLOADED>

[child] = await Child.fetch_related([child], ((Child.parent,),))

child.parent # <Parent>
```

`fetch_related` accepts a `tuple[tuple[Relationship]]` to allow for fetching multiple relationships and deeply nested relationships.

<em>Note: The API of</em> `fetch_related` <em>will be simplified in an upcoming release to accept a wider range of more convenient model and relationship formats.</em>

### Fetching reverse foreign key relationships
```python

parent = await Parent.fetch_one(Parent.id == 1)

parent.children # <p3orm.table.UNLOADED>

[parent] = await Parent.fetch_related([parent], ((Parent.children),))

parent.children # <list[Child]>
```

### Fetching multiple relationships
```python

thing = await Thing.fetch_one(Thing.id == 1)

[thing] = await Thing.fetch_related([thing], ((thing.f1,), (thing.f2,), (thing.rr1)))

thing.f1 # <Model>
thing.f2 # <Model2>
thing.rr1 # <list[Model3]>

```

# Fetching deeply nested relationships
```python

thing = await Thing.fetch_one(Thing.id == 1)

[thing] = await Thing.fetch_related([thing], ((thing.children, thing.children.child)))

thing.children # <list[Child]>

thing.children[0].child # <Child>

```
