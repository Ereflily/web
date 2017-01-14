import asyncio,inspect
from aiohttp import web

async def index(*, name):
	await asyncio.sleep(1)
	return {'name':name}

async def init(loop):
	app = web.Application(loop = loop,middlewares=[unknownFactory])
	app.router.add_route("GET", '/{name}.html', handler(index))
	src = await loop.create_server(app.make_handler(), '127.0.0.1', 23456)
	return src

async def unknownFactory(app, handler):
	async def unknown(request):
		r = await handler(request)
		print(r)
		return web.Response(content_type='text/html',body=bytes(r['name'],encoding='utf8'))
	return unknown

class handler():
	def __init__(self, func):
		self._func = func

	async def __call__(self,request):
		s = inspect.signature(self._func).parameters.keys()
		a = request.match_info.keys()
		kw = {}
		for name, value in request.match_info.items():
			kw[name] = value
		return await self._func(**kw)

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()