# -*- coding: utf-8 -*-
__author__ = 'Ernie Peng'

import logging;logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from jinja2 import Environment, FileSystemLoader
from config_default import config

import orm
from webframe import add_static, add_routes

def init_jinja2(app, **kw):
    logging.info("init jinja2...")
    option = {
        'autoescape' : kw.get('autoescape', True),
        'block_start_string' : kw.get("block_start_string", '{%'),
        'block_end_string' : kw.get('block_end_string', '%}'),
        'variable_start_string' : kw.get("variable_start_string", "{{"),
        'variable_end_string' : kw.get("variable_end_string", '}}'),
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