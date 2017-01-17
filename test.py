import asyncio,inspect
from aiohttp import web
from webframe import add_routes,add_static
from Model.Article import Article
from orm import create_pool
# async def index(*, name):
# 	await asyncio.sleep(1)
# 	return {'name':name}
#
# async def init(loop):
# 	app = web.Application(loop = loop,middlewares=[unknownFactory])
# 	app.router.add_route("GET", '/{name}.html', handler(index))
# 	src = await loop.create_server(app.make_handler(), '127.0.0.1', 23456)
# 	return src
#
# async def unknownFactory(app, handler):
# 	async def unknown(request):
# 		r = await handler(request)
# 		print(r)
# 		return web.Response(content_type='text/html',body=bytes(r['name'],encoding='utf8'))
# 	return unknown
#
# class handler():
# 	def __init__(self, func):
# 		self._func = func
#
# 	async def __call__(self,request):
# 		s = inspect.signature(self._func).parameters.keys()
# 		a = request.match_info.keys()
# 		kw = {}
# 		for name, value in request.match_info.items():
# 			kw[name] = value
# 		return await self._func(**kw)
#
# loop = asyncio.get_event_loop()
# loop.run_until_complete(init(loop))
# loop.run_forever()

# async def init(loop):
#     app = web.Application(loop = loop)
#     # app.router.add_route("GET", '/{name}.html', RequestHandler(index))
#     # add_route(app, index)
#     # add_route(app, blog)
#     add_routes(app, 'handler')
#     add_static(app)
#     srv = await loop.create_server(app.make_handler(), '127.0.0.1', 23456)
#     return srv

async def init(loop):
    article = Article()
    loop = asyncio.get_event_loop()
    await create_pool(loop, database='test')
    s = await article.find().all()
    s = await article.find().all()
    #await user.save()
    print(s)
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()