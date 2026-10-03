"""Exercise a real aiohttp session against a local HTTP server."""

import aiohttp
from aiohttp import web

from custom_components.avamet.api import AvametClient


async def test_real_session_with_bounded_download(html):
    async def handle(request):
        assert request.headers["User-Agent"].startswith("ha-avamet/")
        return web.Response(text=html, content_type="text/html")

    application = web.Application()
    application.router.add_get("/station", handle)
    runner = web.AppRunner(application)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            client = AvametClient(session, "c13m207e02")
            client.url = f"http://127.0.0.1:{port}/station"
            observation = await client.async_get_observation()
            assert observation.values["temperature_c"] == 30.1
            assert observation.values["pressure_hpa"] == 1015
    finally:
        await runner.cleanup()
