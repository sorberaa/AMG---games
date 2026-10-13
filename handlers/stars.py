"""Обработчик магазина Telegram Stars (XTR / Звёзды)."""
import logging
import random
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (CallbackQuery, InlineKeyboardButton as Btn,
                           InlineKeyboardMarkup, LabeledPrice, Message,
                           PreCheckoutQuery)

import data
import db
from data import CAR_CATALOG, STARS_PACKS, fmt
from utils import safe_edit, send_menu

router = Router(name="stars")
log = logging.getLogger("amg.stars")


def stars_catalog_text(player: dict) -> str:
    vip_badge = ""
    if db.is_vip(player):
        vip_badge = f"\n👑 <b>Твой VIP-статус активен</b> (до {player.get('vip_until', '—')})"

    nitro_badge = ""
    if db.is_nitro_boosted(player):
        nitro_badge = f"\n🔥 <b>Нитро-ускорение активно</b> (до {player.get('nitro_boost_until', '—')})"

    return (
        "⭐ <b>ЗВЁЗДНЫЙ МАГАЗИН AMG (TELEGRAM STARS)</b> ⭐\n\n"
        "Здесь ты можешь поддержать проект и мгновенно получить ценные бонусы, "
        "статусную корону 👑, эксклюзивные спорткары и энергию!\n\n"
        "🛡 <i>Все покупки официальны и безопасны через Telegram Stars (XTR).</i>"
        f"{vip_badge}{nitro_badge}\n\n"
        "<b>Выбери интересующий пакет ниже:</b>"
    )


def pack_details_text(pack: dict, player: dict) -> str:
    lines = [
        f"{pack['emoji']} <b>{pack['title']}</b>",
        f"⭐️ <b>Стоимость:</b> {pack['stars']} ⭐️ (Telegram Stars)\n",
        f"📝 <b>Описание:</b>\n{pack['desc']}\n",
        "🎁 <b>Что входит в пакет:</b>"
    ]
    if pack.get("refill_energy"):
        lines.append("• ⚡ <b>Мгновенное пополнение энергии</b> до 100%")
    if pack.get("nitro_hours"):
        lines.append(f"• 🔥 <b>Нитро-ускоритель (+15% к победе)</b> на {pack['nitro_hours']} часа")
    if pack.get("bonus_coins"):
        lines.append(f"• 🪙 <b>{pack['bonus_coins']} монет</b> на игровой баланс")
    if pack.get("bonus_money"):
        lines.append(f"• 💵 <b>${fmt(pack['bonus_money'])}</b> на тюнинг и запчасти")
    if pack.get("bonus_xp"):
        lines.append(f"• 📈 <b>+{pack['bonus_xp']} XP</b> к уровню")
    if pack.get("vip_days"):
        lines.append(f"• 👑 <b>VIP-статус на {pack['vip_days']} дней</b> (корона в нике, +3 к баку энергии)")
    if pack.get("give_car"):
        car = CAR_CATALOG.get(pack["give_car"])
        car_name = car["name"] if car else pack["give_car"]
        lines.append(f"• 🏎 <b>Эксклюзивное авто:</b> {car_name}")
    if pack.get("insurance"):
        lines.append(f"• 🛡 <b>{pack['insurance']} страховки AMG</b> от поломок и арестов")
    if pack.get("case_drop"):
        lines.append("• 🧰 <b>Шанс 25% на моментальный спорткар S-класса</b>")

    lines.append("\n💡 <i>Оплата списывается с баланса звёзд твоего Telegram в 1 клик.</i>")
    return "\n".join(lines)


@router.message(Command("stars"))
@router.message(Command("donate"))
async def cmd_stars(message: Message, player: dict):
    from kb import stars_shop_kb
    await send_menu(message, message.from_user.id, stars_catalog_text(player), stars_shop_kb())


@router.callback_query(F.data == "stars_shop")
async def cb_stars_shop(cb: CallbackQuery, player: dict):
    await cb.answer()
    from kb import stars_shop_kb
    await safe_edit(cb, stars_catalog_text(player), stars_shop_kb())


@router.callback_query(F.data.startswith("stars:view:"))
async def cb_stars_view(cb: CallbackQuery, player: dict):
    await cb.answer()
    pack_id = cb.data.split(":")[2]
    pack = STARS_PACKS.get(pack_id)
    if not pack:
        return await cb.answer("Пакет не найден", show_alert=True)

    from kb import stars_pack_kb
    await safe_edit(cb, pack_details_text(pack, player), stars_pack_kb(pack_id, pack["stars"]))


@router.callback_query(F.data.startswith("stars:buy:"))
async def cb_stars_buy(cb: CallbackQuery, player: dict):
    await cb.answer()
    pack_id = cb.data.split(":")[2]
    pack = STARS_PACKS.get(pack_id)
    if not pack:
        return await cb.answer("Пакет не найден", show_alert=True)

    # В групповых чатах инвойс пользователю отправлять небезопасно — перенаправляем в личные сообщения
    if cb.message.chat.type != "private":
        bot_info = await cb.bot.get_me()
        url = f"https://t.me/{bot_info.username}?start=stars_{pack_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="⭐️ Оплатить в личке с ботом", url=url)],
            [Btn(text="◀️ Назад", callback_data="stars_shop")]
        ])
        return await cb.message.answer(
            f"⭐️ Оплата пакета <b>{pack['title']}</b> ({pack['stars']} ⭐️) проводится в личных сообщениях с ботом для твоей безопасности:",
            reply_markup=kb
        )

    prices = [LabeledPrice(label=pack["title"], amount=pack["stars"])]
    await cb.message.answer_invoice(
        title=pack["title"],
        description=pack["short_desc"],
        payload=f"stars:{pack_id}:{cb.from_user.id}",
        currency="XTR",
        prices=prices,
        provider_token="",  # Для Telegram Stars provider_token всегда пустой
        start_parameter=f"stars_{pack_id}"
    )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, player: dict):
    sp = message.successful_payment
    payload = sp.invoice_payload or ""
    parts = payload.split(":")
    if len(parts) < 3 or parts[0] != "stars":
        log.warning("Неизвестный payload платежа: %s", payload)
        return

    pack_id = parts[1]
    pack = STARS_PACKS.get(pack_id)
    if not pack:
        log.error("Пакет %s не найден при успешной оплате!", pack_id)
        return

    user_id = message.from_user.id
    stars_amount = sp.total_amount
    charge_id = sp.telegram_payment_charge_id

    # Фиксируем транзакцию в базе данных
    await db.record_stars_payment(user_id, pack_id, stars_amount, charge_id)

    received_lines = []

    # 1. Пополнение энергии
    if pack.get("refill_energy"):
        p = await db.get_player(user_id)
        max_e = p.get("max_energy", 10) if p else 10
        await db.update_player(user_id, energy=max_e)
        received_lines.append(f"• ⚡ Энергия полностью восстановлена: <b>{max_e}/{max_e}</b>")

    # 2. Нитро-буст
    if pack.get("nitro_hours"):
        await db.add_nitro_boost(user_id, pack["nitro_hours"])
        received_lines.append(f"• 🔥 Нитро-ускоритель активирован на <b>{pack['nitro_hours']} часа</b>!")

    # 3. Монеты
    if pack.get("bonus_coins"):
        await db.add_coins(user_id, pack["bonus_coins"], reason=f"Telegram Stars: {pack['title']}")
        received_lines.append(f"• 🪙 Начислено монет: <b>+{pack['bonus_coins']}</b>")

    # 4. Игровые доллары на тюнинг
    if pack.get("bonus_money"):
        cur_money = player.get("money", 0)
        await db.update_player(user_id, money=cur_money + pack["bonus_money"])
        received_lines.append(f"• 💵 Средства на тюнинг: <b>+${fmt(pack['bonus_money'])}</b>")

    # 5. Опыт
    if pack.get("bonus_xp"):
        lvl, leveled = await db.add_xp(user_id, pack["bonus_xp"])
        lvl_up_text = f" (🎉 Новый уровень: <b>{lvl}</b>!)" if leveled else ""
        received_lines.append(f"• 📈 Опыт: <b>+{pack['bonus_xp']} XP</b>{lvl_up_text}")

    # 6. VIP-статус
    if pack.get("vip_days"):
        await db.add_vip(user_id, pack["vip_days"], energy_bonus=pack.get("energy_bonus", 3))
        received_lines.append(f"• 👑 <b>VIP-статус активирован на {pack['vip_days']} дней</b> (корона в нике и увеличенный бак энергии)!")

    # 7. Выдача машины
    if pack.get("give_car"):
        car_key = pack["give_car"]
        car_id = await db.add_car(user_id, car_key)
        await db.select_car(user_id, car_id)
        car = CAR_CATALOG.get(car_key)
        car_name = car["name"] if car else car_key
        received_lines.append(f"• 🏎 В гараж доставлен: <b>{car_name}</b> (выбран основным)!")

    # 8. Страховка
    if pack.get("insurance"):
        cur_ins = player.get("has_insurance", 0)
        await db.update_player(user_id, has_insurance=cur_ins + pack["insurance"])
        received_lines.append(f"• 🛡 Выдано страховок: <b>+{pack['insurance']} шт.</b>")

    # 9. Дроп кейса
    if pack.get("case_drop"):
        roll = random.random()
        if roll < 0.25:
            await db.add_car(user_id, "amg_gt")
            received_lines.append("• 🎁 <b>СУПЕР-ПРИЗ ИЗ КЕЙСА:</b> В твой гараж выбит <b>Mercedes-AMG GT</b> (класс S)!")
        elif roll < 0.60:
            await db.add_coins(user_id, 35, reason="Дроп из Звёздного кейса")
            received_lines.append("• 🎁 <b>Приз из кейса:</b> Дополнительно +35 монет 🪙!")
        else:
            await db.add_xp(user_id, 1000)
            received_lines.append("• 🎁 <b>Приз из кейса:</b> Дополнительно +1 000 XP 📈!")

    rec_text = "\n".join(received_lines)
    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"

    # Личное уведомление владельцу бота о поступлении звёзд
    from config import OWNER_ID, SUPER_ADMINS
    notify_recipients = set([OWNER_ID] + SUPER_ADMINS)
    for admin_id in notify_recipients:
        try:
            await message.bot.send_message(
                admin_id,
                f"⭐️ <b>НОВОЕ ПОСТУПЛЕНИЕ ЗВЁЗД (STARS)!</b>\n\n"
                f"👤 <b>Игрок:</b> {message.from_user.first_name} (@{message.from_user.username or '—'})\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                f"📦 <b>Пакет:</b> {pack['title']}\n"
                f"⭐️ <b>Оплачено:</b> <b>+{stars_amount} ⭐️</b>\n"
                f"🧾 <b>Транзакция:</b> <code>{charge_id}</code>\n\n"
                f"💰 <i>Звёзды зачислены на баланс бота!</i>"
            )
        except Exception as e:
            log.warning("Не удалось отправить уведомление о звёздах админу %s: %s", admin_id, e)

    from kb import back_kb
    await message.answer(
        f"{gif_tag}⭐️ <b>СПАСИБО ЗА ПОДДЕРЖКУ! ОПЛАТА УСПЕШНО ПРОШЛА!</b>\n\n"
        f"Ты приобрёл: <b>{pack['title']}</b> за <b>{stars_amount} ⭐️</b>\n\n"
        f"<b>Активированные бонусы:</b>\n{rec_text}\n\n"
        "🏎 <i>Твои новые возможности уже доступны в игре. Газ в пол!</i>",
        reply_markup=back_kb("menu", "🏠 В главное меню")
    )


