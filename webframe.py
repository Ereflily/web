# -*- coding: utf-8 -*-
__author__ = 'Ernie Peng'

import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web

def get(path):
    def decorator(func):
        @functools.wraps(func)
        def wrap(*args, **kw):
            return func(*args, **kw)
        wrap.__method__ = 'GET'
        wrap.__route__ = path
        return wrap
    return decorator

def post(path):
    def decorator(func):
        @functools.wraps()
        def wraps(*args, **kw):
            return func(*args, **kw)
        wraps.__method__ = 'POST'
        wraps.__route__ = path
        return wraps
    return decorator

def hasRequestArgs(func):
    rs = False
    for name, value in inspect.signature(func).parameters.items():
        if name == 'request':
            rs = True
        if rs and (value.kind != inspect.Parameter.VAR_POSITIONAL and value.kind != inspect.Parameter.VAR_KEYWORD and value.kind != inspect.Parameter.KEYWORD_ONLY):
            raise ValueError("request must be last parameters in function: {}{}".format(func.__name__, str(inspect.signature(func))))
    return rs

class RequestHandler():
    def __init__(self, func):
        self._func = func
        self._requiredArgs = inspect.signature(func).parameters.keys()
        self._hasRequestArgs = hasRequestArgs(func)

    async def __call__(self, request):
        kw = {}
        if len(self._requiredArgs) > 0:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith("application/json"):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith("application/x-www-form-urlencoded") or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v
        for name, value in request.match_info.items():
            if name in self._requiredArgs:
                kw[name] = value
        if self._hasRequestArgs:
            kw['request'] = request
        for key in self._requiredArgs:
            if not key in kw:
                return web.HTTPBadRequest('Missing argument: %s' % key)
        args = {}
        for key in kw:
            if key in self._requiredArgs:
                args[key] = kw[key]
        return await self._func(**args)

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    app.router.add_static('/static/', path)
    logging.info('add static  {}'.format(path))

def add_route(app, func):
    method = getattr(func, '__method__', None)
    path = getattr(func, '__route__', None)
    if method is None or path is None:
        

async def index(*, name, request):
    return web.Response(content_type='text/html', body=bytes(name, encoding='utf8'))

async def init(loop):
    app = web.Application(loop = loop)
    #app.router.add_route("GET", '/{name}.html', RequestHandler(index))
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 23456)
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()