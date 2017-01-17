import orm
from orm import Model
class Article(Model):
    id = orm.IntegerField('id', primary_key=True)
    title = orm.StringField('title', type='varchar(30)')
    content = orm.StringField('content', type="mediumtext")
    catid = orm.IntegerField('catid', type='tinyint')
    tag = orm.StringField('tag', type='varchar(25)')
    description = orm.StringField('description')
    created_at = orm.IntegerField('created_at')
    comment_count = orm.IntegerField('comment_count')
    view_count = orm.IntegerField("view_count")