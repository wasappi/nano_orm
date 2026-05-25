from nano_orm import database
from nano_orm.orm import BaseModel, CharField, IntegerField

database.initialize_db()

class Product(BaseModel):
    name = CharField(required=True)
    price = IntegerField()


print("Create table ...")
Product.create_table()
print("Table succesfully created !")

# print("Create 1st reccord")
#prod3 = Product.create(name="TO delete", price=999)
# prod2 = Product.create(name="Keychron B1", price=49)

# print(prod1)
# print(prod2)

print("\n Search all products :")
all_products = Product.search()
for p in all_products:
    print(p)

print("\n Search specific product (price = 49) :")
specific_product = Product.search(price=49)
print(specific_product)

product_2 = Product.get(2)
if product_2.update(price=59):
    print(product_2)

product_3 = Product.get(3)
product_3.delete()

print("\n Search all products :")
all_products = Product.search()
for p in all_products:
    print(p)