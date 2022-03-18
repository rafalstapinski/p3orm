# Multiple Databases

By default, p3orm provides a singleton to connect to an available database as `p3orm.core.Porm`.

You can create your own instance of a `_Porm` and connect to a second database, though.

```python
from p3orm import _Porm

first_database = _Porm()
await first_database.connect(dsn=...)

second_database = _Porm()
await second_Database.connect(user=..., password=..., database=..., host=..., port=...)
```
