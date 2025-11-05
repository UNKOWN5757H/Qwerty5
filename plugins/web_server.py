# This is a minimal web server to pass health checks on Koyeb/Render
# It does NOT stream files.

from aiohttp import web
from info import PORT

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running"})

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app
