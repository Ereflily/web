from webframe import get
from aiohttp import web

@get('/{name}.html')
def index(*, name, request):
    return web.Response(content_type='text/html', body=bytes(name, encoding='utf8'))

@get('/blog/{id}.html')
def blog(*, id, request):
    return web.Response(content_type='text/html', body=bytes(id, encoding='utf8'))
