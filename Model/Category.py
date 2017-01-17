from orm import Model
import orm
class Category(Model):
    id = orm.IntegerField('id', primary_key=True, type='tinyint')
    name = orm.StringField('name', type='varchar(18)')
    article_count = orm.IntegerField("article_count", type='tinyint')
    pid = orm.IntegerField('pid', type='tinyint')