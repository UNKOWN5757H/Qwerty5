from aiohttp import web

# Assuming 'route' is imported from 'Qwerty5.plugins.route'
# and contains the list of web routes.
# If 'route' isn't automatically imported, you might need:
# from Qwerty5.plugins import route
# Or, if the routes list inside 'route.py' is named 'routes':
# from Qwerty5.plugins.route import routes as route_list

# Define web_app. The original might have options like client_max_size.
web_app = web.Application() 

async def web_server():
    """
    Initializes and returns the aiohttp web application.
    """
    
    # FIX: Changed 'routes' to 'route'.
    # The NameError suggested 'routes' was not defined,
    # but 'route' (likely imported from Qwerty5/plugins/route.py) was.
    try:
        # We try to use 'route' as suggested by the NameError
        web_app.add_routes(route)
    except NameError:
        # Fallback in case 'route' isn't defined either,
        # and the user needs to check their imports.
        print("Error: 'route' variable not found.")
        print("Please ensure your web routes are imported correctly in plugins/__init__.py")
        # As a last resort, if the variable was *meant* to be 'routes',
        # this will just fail again, but we've tried the fix.
        web_app.add_routes(routes) 
        
    return web_app
