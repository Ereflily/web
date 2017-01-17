# -*- coding: utf-8 -*-
__author__ = 'Ernie Peng'

import logging;logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from my_config import config

import orm
from webframe import add_static, add_routes

def init_jinja2(app, **kw):
    logging.info("init jinja2...")
    option = {
        'autoescape' : kw.get('autoescape', True),
        'block_start_string' : kw.get("block_start_string", '<?python'),
        'block_end_string' : kw.get('block_end_string', '?>'),
        'variable_start_string' : kw.get("variable_start_string", "<?="),
        'variable_end_string' : kw.get("variable_end_string", '=?>'),
        'auto_reload' : kw.get("auto_reload", True)
    }
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info("set jinja2 template path :{}".format(path))
    env = Environment(loader=FileSystemLoader(path), **option)
    filter = kw.get('filter', None)
    if filter is not None:
        for name, value in filter.items():
            env.filters[name] = value
    app['__template__'] = env

async def responseFactory(app, handler):
    async def response(request):
        logging.info("response handler..")
        rs = await handler(request)
        if isinstance(rs, web.StreamResponse):
            return rs
        if isinstance(rs, bytes):
            return web.Response(body=rs,content_type="application/octet-stream")
        if isinstance(rs, str):
            if rs.startswith("redirect:"):
                return web.HTTPFound(rs[9:])
            return web.Response(body=bytes(rs,encoding='utf8'),content_type="text/html",charset='utf8')
        if isinstance(rs, dict):
            if rs['__template__'] is not None:
                return web.Response(body=app['__template__'].get_template(rs['__template__'] + '.html').render(**rs).encode('utf-8'), content_type='text/html')
            else:
                return web.Response(body=json.dump(rs, ensure_ascii=False, default=lambda o:o.__dict__).encode('utf8'), content_type="text/html", charset='utf8')
    return response

async def init(loop):
    await orm.create_pool(loop, **config['db'])
    app = web.Application(loop=loop, middlewares=[
        responseFactory
    ])
    init_jinja2(app)
    add_routes(app, 'handler')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 2333)
    logging.info("start at 127.0.0.1:2333")
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()