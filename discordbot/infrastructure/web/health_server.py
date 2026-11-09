import time
from typing import Optional
from aiohttp import web
import discord

def create_health_app(bot: discord.Client, start_time: float) -> web.Application:
    app = web.Application()

    async def health_check(request: web.Request) -> web.Response:
        uptime_seconds = int(time.time() - start_time)
        try:
            latency = round(bot.latency * 1000, 2) if bot.latency is not None and not (bot.latency != bot.latency) else None
        except Exception:
            latency = None

        status_data = {
            "status": "healthy" if bot.is_ready() else "starting",
            "bot_user": str(bot.user) if bot.user else None,
            "guilds": len(bot.guilds) if bot.is_ready() else 0,
            "latency_ms": latency,
            "uptime_seconds": uptime_seconds,
        }
        return web.json_response(status_data, status=200)

    async def root_handler(request: web.Request) -> web.Response:
        return web.Response(
            text="Algorhythm Discord Bot is alive and running! 🤖 Visit /health for JSON health metrics.",
            content_type="text/plain"
        )

    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_check)
    return app

async def start_health_server(bot: discord.Client, host: str = "0.0.0.0", port: int = 8080) -> Optional[web.AppRunner]:
    """Starts an asynchronous HTTP health check server alongside the Discord bot."""
    try:
        app = create_health_app(bot, start_time=time.time())
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"🩺 Health check server listening on http://{host}:{port}/health")
        return runner
    except OSError as e:
        print(f"⚠️ Health server could not bind to {host}:{port} ({e}). Bot will continue running.")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error starting health server: {e}. Bot will continue running.")
        return None
