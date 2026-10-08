from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from data import fmt
from kb import main_menu_kb
from utils import safe_edit, send_menu

router = Router(name="menu")


def menu_text(p: dict) -> str:
    return (
        "🏎 <b>AMG RACING</b>\n\n"
        f"👤 {p['first_name']} · ур. <b>{p['level']}</b>\n"
        f"💰 ${fmt(p['money'])} · 🪙 {fmt(p['coins'])} · ⚡ {p['energy']}/{p['max_energy']}\n\n"
        "Выбери раздел:"
    )


WELCOME = (
    "🏎 <b>AMG RACING</b> 🏎\n\n"
    "Добро пожаловать в мир уличных гонок Mercedes-AMG!\n\n"
    "🚗 Собирай коллекцию из 21 AMG — от C180 до AMG ONE\n"
    "🔧 Прокачивай мотор, турбину, нитро и ещё 4 узла\n"
    "🏁 Гоняй против уличных легенд\n"
    "⚔️ Вызывай друзей на дуэли со ставками прямо в чате\n"
    "🪙 Копи монеты на кейсы и бусты\n\n"
    "💰 Стартовый капитал: <b>$50 000</b>\n"
    "🚗 Первая машина: <b>Mercedes C180</b>"
)

HELP = (
    "❓ <b>Как играть</b>\n\n"
    "🏁 <b>Гонки</b> — тратят 1 ⚡ энергию (восстанавливается 1 ед. / 20 мин). "
    "Гонка состоит из 5 этапов: старт, прямая, поворот, спринт, финиш. "
    "На каждом этапе важны разные характеристики.\n\n"
    "⚔️ <b>Дуэли</b> — создай вызов со ставкой, любой игрок может принять. "
    "В группе: <code>/duel 5000</code>\n\n"
    "🔧 <b>Тюнинг</b> — 7 узлов по 5 уровней. Улучшения применяются к выбранной машине.\n\n"
    "🪙 <b>Монеты</b> — за гонки, бонусы и достижения. Тратятся на энергию, кейсы и опыт.\n\n"
    "🎁 <b>Бонус дня</b> — заходи каждый день, награда растёт 7 дней подряд.\n\n"
    "<b>Команды:</b>\n"
    "/menu — главное меню\n/profile — профиль\n/garage — гараж\n"
    "/race — гонки\n/duel [ставка] — вызов в чате\n/daily — бонус\n/top — рейтинг"
)


@router.message(CommandStart())
async def cmd_start(message: Message, player: dict):
    await message.answer(WELCOME)
    await send_menu(message, message.from_user.id, menu_text(player), main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message, player: dict):
    await send_menu(message, message.from_user.id, menu_text(player), main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP)


@router.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery, player: dict):
    await cb.answer()
    await safe_edit(cb, menu_text(player), main_menu_kb())


@router.callback_query(F.data == "help")
async def cb_help(cb: CallbackQuery):
    await cb.answer()
    from kb import back_kb
    await safe_edit(cb, HELP, back_kb())


@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer("Уже на максимуме!")

