"""AMG Racing — Telegram мини-RPG. Точка входа."""
import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN, PORT
from db import init_db
from handlers import all_routers
from utils import AccessMiddleware, reload_admins

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("amg")


async def health(_request):
    return web.Response(text="OK")


async def start_web():
    """Мини веб-сервер — нужен Render для health-check и чтобы сервис не засыпал."""
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Health server on :%s", PORT)
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
        BotCommand(command="duel", description="⚔️ Вызов на дуэль [ставка]"),
        BotCommand(command="garage", description="🚗 Гараж"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="daily", description="🎁 Бонус дня"),
        BotCommand(command="top", description="🏆 Рейтинг"),
        BotCommand(command="help", description="❓ Помощь"),
    ])

    runner = await start_web()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Bot polling started")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

