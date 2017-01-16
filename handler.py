from webframe import get
from aiohttp import web

@get('/blog/{id}.html')
def blog(*, id, request):
    return web.Response(content_type='text/html', body=bytes(id, encoding='utf8'))

@get('/')
def index():
    return "hello"