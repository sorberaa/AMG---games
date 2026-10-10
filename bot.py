"""AMG Racing — Telegram мини-RPG. Точка входа."""
import asyncio
import logging

from pathlib import Path

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN, PORT
from data import CAR_CATALOG
from db import init_db
from handlers import all_routers
from utils import AccessMiddleware, reload_admins

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("amg")

BASE_DIR = Path(__file__).resolve().parent
STATIC_INDEX = BASE_DIR / "static" / "index.html"


async def health(_request):
    return web.Response(text="OK")


async def index_handler(_request):
    if STATIC_INDEX.exists():
        return web.Response(text=STATIC_INDEX.read_text(encoding="utf-8"), content_type="text/html")
    return web.Response(text="AMG Racing Bot Online", content_type="text/plain")


async def api_status(request):
    bot: Bot | None = request.app.get("bot")
    bot_username = "AmgRaceBot"
    if bot:
        try:
            me = await bot.get_me()
            if me and me.username:
                bot_username = me.username
        except Exception:
            pass
    return web.json_response({
        "status": "ok",
        "online": True,
        "bot_username": bot_username,
        "cars_count": len(CAR_CATALOG),
        "service": "AMG Racing",
        "version": "2.1.0",
    })


async def start_web(bot: Bot | None = None):
    """Мини веб-сервер — нужен Render для health-check, фирменного лоадера и API."""
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", index_handler)
    app.router.add_get("/health", health)
    app.router.add_get("/api/status", api_status)
    static_dir = BASE_DIR / "static"
    if static_dir.exists():
        app.router.add_static("/static/", str(static_dir))
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
        log.info("Health & Web server on :%s", PORT)
    except Exception as e:
        log.warning("Web port %s busy (%s), continuing polling", PORT, e)
    return runner


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан!")
    await init_db()
    await reload_admins()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(AccessMiddleware())
    dp.callback_query.outer_middleware(AccessMiddleware())
    for r in all_routers:
        dp.include_router(r)

    await bot.set_my_commands([
        BotCommand(command="menu", description="🏠 Главное меню"),
        BotCommand(command="race", description="🏁 Гонки"),
        BotCommand(command="duel", description="⚔️ Дуэль [ставка/монеты]"),
        BotCommand(command="boss", description="👾 Рейд на босса в чате"),
        BotCommand(command="adventure", description="🌃 Ночные похождения по автобану"),
        BotCommand(command="wheel", description="🎰 Колесо Фортуны AMG"),
        BotCommand(command="drag", description="🚦 Драг-рейсинг 402м"),
        BotCommand(command="tournament", description="🏆 Гран-при турнир чата"),
        BotCommand(command="chase", description="🚓 Погоня от полиции"),
        BotCommand(command="quiz", description="🧠 AMG Авто-викторина"),
        BotCommand(command="airdrop", description="📦 Сброс лутбокса AMG"),
        BotCommand(command="royale", description="💥 Королевская битва / Гонка на выбывание"),
        BotCommand(command="garage", description="🚗 Гараж"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="daily", description="🎁 Бонус дня"),
        BotCommand(command="top", description="🏆 Рейтинг"),
        BotCommand(command="help", description="❓ Помощь"),
    ])



    runner = await start_web(bot)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Bot polling started")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

