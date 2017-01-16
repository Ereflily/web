from webframe import get
from aiohttp import web
from Model.User import User
import logging;logging.basicConfig(level=logging.INFO)

@get('/blog/{id}.html')
def blog(*, id, request):
    return web.Response(content_type='text/html', body=bytes(id, encoding='utf8'))

@get('/')
async def index():
    return {
        '__template__' : 'test',
    }