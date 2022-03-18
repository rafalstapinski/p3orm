# Defining models

## Defining a table

Models are used in p3orm to reflect the tables in your database. They can be created by defining a class the inherits from `p3orm.table.Table`.

```python
from p3orm import Table

class MyTable(Table):
  __tablename__ = "my_table"
```

All p3orm models require a `__tablename__` property which must match name of the table in your database.

## Defining columns

Your models define tables using the `Column` function.

```python
from datetime import datetime
from typing import Optional
from p3orm import Table, Column

class MyTable(Column):
  __tablename__ = "my_table"

  id = Column(int, pk=True, autogen=True)
  name = Column(Optional[str])
  property_name = Column(str, "column_name")
  created_at = Column(datetime, autogen=True)
```

Each column has can be defined with the following parameters

* `_type` - This is a positional argument. It is the first and only required argument you must pass to define your column. It is what p3orm will use to serialize and deserialize the value between Python and the database. 
* `column_name` - This is the name of the column in the database. If not specified, p3orm will use the name of the field as the column name.
* `pk`- This is a boolean flag which tells p3orm that this column is the primary key of your table.
* `autogen` - This is a boolean flag which tells p3orm that this column has a `DEFAULT` constant or expression value in the database.

## Column types

p3orm uses <a href="https://github.com/samuelcolvin/pydantic">Pydantic</a> under the hood to map query results into Python objects.  All standard data types are supported out of the box, including numbers, text, arrays, composite types, range types, enumerations and any combination of them.

p3orm also uses these types for intellisense within your IDE, so your models' field types will be automatically inferred by your editor!

For a list of supported types, see the <a href="https://magicstack.github.io/asyncpg/current/usage.html#type-conversion" >asyncpg docs</a>.
### Optional types and nullable columns

If a column is nullable/optional in the database, its type should be `Optional[ ]` (or `| None`).

When a field is required/not-nullable:

* p3orm will raise a `pydantic.error_wrappers.ValidationError` if you try to create an instance of the object locally without providing a non-null value.
* p3orm will raise an `asyncpg.exceptions.NotNullViolationError` if you fetch an object from the database which has a null value.

A model's fields' optionality should match the nullability of the column in the database.
## Default columns

Column marked with `autogen=True` are columns whose values are generated at the database layer. Marking a field with `autogen=True` tells p3orm to ignore user-defined values in the `Table`'s insert and update statements. Locally changing the value of one of these fields on a model will not raise an error, but persisting that change to the database will have no effect. This feature is used for columns like `created_at`, `updated_at`, or auto incrementing IDs.
