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

def getKeyWordArgs(func):
    args = []
    for name,value in inspect.signature(func).parameters.items():
        if value.kind == 'KEYWORD_ONLY' and value.default == inspect.Parameter.empty:
            args.append(name)