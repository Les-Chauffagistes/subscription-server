from typing import cast
from dotenv import load_dotenv

load_dotenv(".env")

from init import log, routes, app, log
from src.cors import cors
from os import getenv, environ
from aiohttp import web
from asyncio import new_event_loop, set_event_loop, Future
from src.constants import *

for key in [APPLICATION_MODE, SERVER_PORT, OPENNODE_API_KEY, OPENNODE_API_URL, CALLBACK_URL]:
    if key not in environ:
        log.crit(f"{key} is missing")
        exit(1)

async def main():
    log.info("Démarrage du serveur...")
    
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", int(cast(str, getenv(SERVER_PORT))))
    await site.start()
    log.info(f"Serveur interne en ligne sur localhost:{getenv(SERVER_PORT)}")

    await Future()


if __name__ == "__main__":
    from src import v1, health

    from src.v1.app import routes as v1_routes
    app.add_routes(routes)
    app.add_routes(v1_routes)
    paths = []
    for route in app.router.routes():
        log.info("added cors on", route.method, route.handler.__name__)
        cors.add(route)

    loop = new_event_loop()
    set_event_loop(loop)
    try:
        loop.run_until_complete(main())

    except KeyboardInterrupt:
        log.info("Bye")
        exit(0)
