import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from datetime import datetime
import pytz
import re

import gspread
from google.oauth2 import service_account

TOKEN = '7653332960:AAGWP4vmKyaoQ-8dYyR9XIm7j0G-9aoHwnE'
ADMIN_ID = 6425885445

SUPPORT_TEXT = (
    "💬 <b>Поддержка</b>\n\n"
    "Если возникли вопросы, обращайтесь:\n"
    "Телефон: +7 999 255-28-54\n"
    "Telegram: @realBalticBike\n"
    "E-mail: velo.prokat@internet.ru"
)

PHONE_NUMBER = "+7 906 211-29-40"

bike_categories = {
    'Детский':     {"hour": 150, "emoji": "🧒"},
    'Прогулочный': {"hour": 200, "emoji": "🚲"},
    'Спортивный':  {"hour": 250, "emoji": "🚴"},
    'Фэтбайк':     {"hour": 300, "emoji": "🌄"},
}

QUANTITY_CHOICES = [1, 2, 3, 4, 5]
user_rent_data = {}

KALININGRAD_TZ = pytz.timezone('Europe/Kaliningrad')

# ---- Google Sheets ----
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = "balticbikebot-8f325aae06ee.json"
SPREADSHEET_ID = '1OeqJkQRkyqlkgPuorni6CQzwjY4RP9rB1sRCdtCL07g'
SHEET_NAME = 'Лист1'

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
gc = gspread.authorize(creds)
worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

def write_rent_to_sheet(event_type, user_fullname, user_id, phone, start_time, end_time, duration_str, cart, total_price):
    cart_str = "; ".join([f"{bike_categories[cat]['emoji']} {cat}: {qty} шт." for cat, qty in cart.items()])
    worksheet.append_row([
        event_type,            # "Начало аренды" или "Завершена аренда"
        user_fullname,
        str(user_id),
        phone or "",
        start_time.strftime("%d.%m.%Y %H:%M") if start_time else "",
        end_time.strftime("%d.%m.%Y %H:%M") if end_time else "",
        duration_str or "",
        cart_str,
        str(total_price)
    ])

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

def main_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Арендовать велосипед")],
            [types.KeyboardButton(text="Перезапустить бот"), types.KeyboardButton(text="Поддержка")]
        ],
        resize_keyboard=True
    )

def categories_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(
                    text=f"{bike_categories[cat]['emoji']} {cat} ({bike_categories[cat]['hour']}₽/ч)"
                )
            ] for cat in bike_categories.keys()
        ] +
        [
            [types.KeyboardButton(text="Посмотреть корзину")],
            [types.KeyboardButton(text="Начать аренду")],
            [types.KeyboardButton(text="Перезапустить бот"), types.KeyboardButton(text="Поддержка")]
        ],
        resize_keyboard=True
    )

def cart_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Очистить корзину")],
            [types.KeyboardButton(text="Назад к выбору категории")]
        ],
        resize_keyboard=True
    )

def during_rent_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Завершить аренду")],
            [types.KeyboardButton(text="Поддержка")]
        ],
        resize_keyboard=True
    )

def contact_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True
    )

@dp.message(F.text == "/start")
async def greet(message: types.Message):
    photo = FSInputFile("welcome.png")
    await message.answer_photo(
        photo,
        caption=(
            "<b>Добро пожаловать в сервис велопроката BalticBike!</b>\n\n"
            "🌊 Прокатитесь по Балтийской косе и побережью на стильных велосипедах!\n"
            "Выберите категорию, добавьте вело в корзину и нажмите <b>«Начать аренду»</b>.\n\n"
            "Желаем приятной поездки! 🚲"
        ),
        reply_markup=main_menu_keyboard()
    )

@dp.message(F.text == "Перезапустить бот")
async def restart_bot(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if data and data.get("is_renting"):
        await message.answer("Нельзя перезапустить бот во время активной аренды. Сначала завершите аренду!")
        return
    keyboard = main_menu_keyboard()
    await message.answer(
        "Бот успешно перезапущен!\n\n"
        "Нажмите «Арендовать велосипед», чтобы начать оформление.",
        reply_markup=keyboard
    )

@dp.message(F.text == "Поддержка")
async def support(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if data and data.get("is_renting"):
        keyboard = during_rent_keyboard()
    elif data and data.get("cart"):
        keyboard = categories_keyboard()
    else:
        keyboard = main_menu_keyboard()
    await message.answer(
        SUPPORT_TEXT,
        reply_markup=keyboard
    )

@dp.message(F.text == "Арендовать велосипед")
async def start_rent_button(message: types.Message):
    user_id = message.from_user.id
    user_rent_data[user_id] = {
        "cart": {},
        "start_time": None,
        "awaiting_quantity": False,
        "last_category": None,
        "is_renting": False,
        "phone": None,
        "asked_phone": False,
    }
    keyboard = categories_keyboard()
    await message.answer("Выберите категорию велосипеда для добавления в корзину:", reply_markup=keyboard)

@dp.message(lambda m: any(m.text and m.text.startswith(bike_categories[cat]['emoji']) for cat in bike_categories))
async def select_category(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_rent_data:
        await start_rent_button(message)
        return
    data = user_rent_data[user_id]
    if data["is_renting"]:
        await message.answer("Аренда уже запущена! Завершите аренду или перезапустите бот.", reply_markup=during_rent_keyboard())
        return

    cat_name = None
    for cat, info in bike_categories.items():
        pattern = f"^{re.escape(info['emoji'])} {cat}"
        if re.match(pattern, message.text):
            cat_name = cat
            break
    if not cat_name:
        await message.answer("Не удалось распознать категорию, попробуйте снова.")
        return

    data["awaiting_quantity"] = True
    data["last_category"] = cat_name

    qty_keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=str(qty)) for qty in QUANTITY_CHOICES],
            [types.KeyboardButton(text="Назад к выбору категории")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"Сколько '{cat_name}' велосипедов добавить?",
        reply_markup=qty_keyboard
    )

@dp.message(F.text == "Назад к выбору категории")
async def back_to_category(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_rent_data:
        user_rent_data[user_id]["awaiting_quantity"] = False
        user_rent_data[user_id]["last_category"] = None
    keyboard = categories_keyboard()
    await message.answer("Выберите категорию велосипеда для добавления:", reply_markup=keyboard)

@dp.message(lambda m: m.from_user.id in user_rent_data and user_rent_data[m.from_user.id]["awaiting_quantity"])
async def select_quantity(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data[user_id]
    if message.text == "Назад к выбору категории":
        await back_to_category(message)
        return
    try:
        qty = int(message.text)
        if qty not in QUANTITY_CHOICES:
            raise ValueError
    except ValueError:
        await message.answer("Выбери количество только из кнопок ниже!")
        return
    cat = data["last_category"]
    data["cart"][cat] = data["cart"].get(cat, 0) + qty
    data["awaiting_quantity"] = False
    data["last_category"] = None
    keyboard = categories_keyboard()
    await message.answer(
        f"Добавлено {qty} '{cat}' велосипед(а).\n\n"
        "Выберите следующую категорию, либо 'Начать аренду', чтобы приступить к прокату.\n"
        "Можно также посмотреть корзину.",
        reply_markup=keyboard
    )

@dp.message(F.text == "Посмотреть корзину")
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if not data or not data["cart"]:
        await message.answer("Ваша корзина пуста!", reply_markup=categories_keyboard())
        return
    cart_str = "\n".join([
        f"{bike_categories[cat]['emoji']} <b>{cat}</b>: {cnt} шт. ({bike_categories[cat]['hour']}₽/ч)" 
        for cat, cnt in data["cart"].items()
    ])
    await message.answer(f"В вашей корзине:\n{cart_str}", reply_markup=cart_keyboard())

@dp.message(F.text == "Очистить корзину")
async def clear_cart(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_rent_data:
        user_rent_data[user_id]["cart"] = {}
        user_rent_data[user_id]["is_renting"] = False
        user_rent_data[user_id]["start_time"] = None
    keyboard = categories_keyboard()
    await message.answer("Корзина очищена!", reply_markup=keyboard)

@dp.message(F.text == "Начать аренду")
async def start_rent(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if not data or not data["cart"]:
        await message.answer("Сначала выберите хотя бы один велосипед.")
        return
    if not data["phone"] and not data["asked_phone"]:
        data["asked_phone"] = True
        await message.answer("Пожалуйста, отправьте свой номер телефона кнопкой ниже для оформления аренды.", reply_markup=contact_keyboard())
        return

    data["start_time"] = datetime.now(KALININGRAD_TZ)
    data["is_renting"] = True
    keyboard = during_rent_keyboard()
    cart_str = "\n".join([
        f"{bike_categories[cat]['emoji']} <b>{cat}</b>: {cnt} шт. ({bike_categories[cat]['hour']}₽/ч)"
        for cat, cnt in data["cart"].items()
    ])

    total_hour_price = 0
    for cat, qty in data["cart"].items():
        total_hour_price += bike_categories[cat]["hour"] * qty

    # Google Sheets запись - НАЧАЛО аренды
    write_rent_to_sheet(
        "Начало аренды",
        message.from_user.full_name,
        message.from_user.id,
        data.get('phone'),
        data["start_time"],
        None,
        "",
        data["cart"],
        total_hour_price
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"НАЧАЛАСЬ АРЕНДА!\n"
            f"User: {message.from_user.full_name}\n"
            f"Телефон: {data['phone'] if data['phone'] else 'Не указан'}\n"
            f"id: {message.from_user.id}\n"
            f"Время: {datetime.now(KALININGRAD_TZ).strftime('%H:%M')}\n"
            f"Корзина:\n{cart_str}"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление админу (начало): {e}")

    await message.answer(
        f"Вы арендовали:\n{cart_str}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>💸 Стоимость всех велосипедов за 1 час: {total_hour_price} руб.</b>\n\n"
        "Когда закончите кататься — нажмите 'Завершить аренду'.",
        reply_markup=keyboard
    )

@dp.message(F.text == "Завершить аренду")
async def finish_rent(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if not data or not data["is_renting"]:
        await message.answer("Вы ещё не начали аренду. Для старта — выберите велосипеды и начните аренду.")
        return
    end_time = datetime.now(KALININGRAD_TZ)
    start_time = data["start_time"]
    duration = end_time - start_time
    minutes = int(duration.total_seconds() // 60)
    if minutes == 0:
        minutes = 1

    start_str = start_time.strftime("%H:%M")
    end_str = end_time.strftime("%H:%M")
    hours_part = minutes // 60
    minutes_part = minutes % 60
    if hours_part > 0:
        ride_time = f"{hours_part} ч {minutes_part} мин"
    else:
        ride_time = f"{minutes_part} мин"
    period_str = f"{start_str} — {end_str}"

    total_price = 0
    lines = []
    for cat, qty in data["cart"].items():
        hour_price = bike_categories[cat]["hour"]
        emoji = bike_categories[cat]['emoji']

        if minutes < 60:
            minute_price = hour_price / 60
            price = int(minute_price * minutes)
            line = f"{emoji} <b>{cat}</b>: {qty} шт. × {minutes} мин × {minute_price:.2f}₽ = {price * qty}₽"
        else:
            hours = minutes // 60
            remain = minutes % 60
            if remain > 45:
                hours += 1
            price = hour_price * hours
            line = f"{emoji} <b>{cat}</b>: {qty} шт. × {hours} ч × {hour_price}₽ = {price * qty}₽"
        lines.append(line)
        total_price += price * qty

    keyboard = main_menu_keyboard()
    await message.answer(
        f"Вы катались {minutes} минут(ы) на:\n"
        + "\n".join(lines) +
        "\n━━━━━━━━━━━━━━━━━━━━"
        f"\n<b>💰 Общая стоимость: <u>{total_price} руб.</u></b>\n\n"
        "<b>💸 Оплата аренды по СБП</b>\n"
        f"Переведите сумму на номер:\n"
        f"<code>{PHONE_NUMBER}</code>\n"
        "Нажмите на номер, чтобы скопировать его.\n"
        "После оплаты покажите чек сотруднику или отправьте его в чат.",
        reply_markup=keyboard
    )

    # Google Sheets запись - ОКОНЧАНИЕ аренды
    write_rent_to_sheet(
        "Завершена аренда",
        message.from_user.full_name,
        message.from_user.id,
        data.get('phone'),
        start_time,
        end_time,
        f"{period_str} ({ride_time})",
        data["cart"],
        total_price
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"АРЕНДА ЗАВЕРШЕНА!\n"
            f"User: {message.from_user.full_name}\n"
            f"Телефон: {data['phone'] if data['phone'] else 'Не указан'}\n"
            f"id: {message.from_user.id}\n"
            f"Время проката: {ride_time}\n"
            f"Период: {period_str}\n"
            + "\n".join(lines) +
            f"\n<b>💰 Общая стоимость: {total_price} руб.</b>"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление админу (окончание): {e}")

    if user_id in user_rent_data:
        del user_rent_data[user_id]

@dp.message(F.content_type == types.ContentType.CONTACT)
async def get_contact(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if not data:
        await message.answer("Сначала начните оформление аренды.")
        return
    data["phone"] = message.contact.phone_number
    await start_rent(message)

@dp.message(F.text == "/myid")
async def my_id(message: types.Message):
    await message.answer(f"Ваш user_id: {message.from_user.id}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
