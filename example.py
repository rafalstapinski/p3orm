
from typing import Optional
from porm.table import Table, PormField

def run():

    class MyTable(Table):
        __tablename__ = "tablename"

        """ end state might be something like:
        id: int = PormField("id", pk=True)
        name: str = PormField("name")
        """

        id: int = PormField(int, "id")
        name: str = PormField(str, "name")
        description: Optional[str] = PormField(Optional[str], "description")

    obj1 = MyTable(id=1, name="obj1")
    obj2 = MyTable(id=2, name="obj2", description="yeeterooni")
    MyTable.insert(obj1, obj2)

    # MyTable.insert(obj1, obj2)

    # q = MyTable.select().where(MyTable.field1 == MyTable.field2)
    # print(q)
    # q = Query.from_("tablename").select(MyTable.field1 - MyTable.field2)
    # print(q)


if __name__ == "__main__":
    run()
