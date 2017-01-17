from webframe import get
from aiohttp import web
from Model.User import User
from Model.Article import  Article
import logging;logging.basicConfig(level=logging.INFO)

@get('/blog/{id}.html')
def blog(*, id, request):
    return web.Response(content_type='text/html', body=bytes(id, encoding='utf8'))

@get('/')
async def index():
    articles = await Article().find().all()
    return {
        '__template__' : 'index',
        'articles' : articles
    }