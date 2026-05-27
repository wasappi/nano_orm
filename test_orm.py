from nano_orm import database
from nano_orm.orm import BaseModel, CharField, IntegerField, BelongsTo, HasMany



# class Product(BaseModel):
#     name = CharField(required=True)
#     price = IntegerField()



class PingResult(BaseModel):
    status_code = IntegerField()
    target = BelongsTo("Target", required=True)

class Target(BaseModel):
    name = CharField(required=True)
    url = CharField(required=True)
    pings = HasMany("PingResult", foreign_key_name="target")


database.init_db("test_watcher.db")
# Target.create_table()
# PingResult.create_table()

# web1 = Target.create(name="API Production", url="https://api.website.com")

# ping1 = PingResult.create(target=web1, status_code=200)
# ping2 = PingResult.create(target=web1, status_code=200)
# ping3 = PingResult.create(target=web1, status_code=500)


# pings = web1.pings
# print("Results: ")
# print(f"{web1.name} has {len(pings)} pings")
# for ping in pings:
#     print(f"{ping.id} - {ping.status_code}")

# web1 = Target.get(3)
# web1.delete()