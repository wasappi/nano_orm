from nano_orm import database
from nano_orm.orm import BaseModel, CharField, IntegerField

database.initialize_db()

class Product(BaseModel):
    name = CharField(required=True)
    price = IntegerField()

print("Create table ...")
Product.create_table()
print("Table succesfully created !")
