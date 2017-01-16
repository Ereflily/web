import orm
from orm import Model
class User(Model):
    id = orm.IntegerField('id', primary_key=True)
    name = orm.StringField('name')
    password = orm.StringField("password")