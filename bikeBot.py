import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from datetime import datetime, date
import pytz
import os
import re
import csv
from collections import Counter

TOKEN = '7653332960:AAGWP4vmKyaoQ-8dYyR9XIm7j0G-9aoHwnE'
ADMIN_ID = 6425885445  # <-- сюда свой user_id

SUPPORT_TEXT = (
    "💬 <b>📞   BalticBike</b>\n\n"
    "Если возникли вопросы:\n"
    "Телефон: <a href='tel:+79992552854'>+7 999 255-28-54</a>\n"
    "Telegram: @realBalticBike\n"
    "E-mail: velo.prokat@internet.ru"
)

PHONE_NUMBER = "+7 906 211-29-40"  # <-- номер для оплаты

bike_categories = {
    'Детский':     {"hour": 150, "emoji": "🧒", "img": "images/Baby.png"},
    'Прогулочный': {"hour": 200, "emoji": "🚲", "img": "images/City.png"},
    'Спортивный':  {"hour": 250, "emoji": "🚵", "img": "images/Sport.png"},
    'Фэтбайк':     {"hour": 300, "emoji": "🌄", "img": "images/Fat.png"},
}

QUANTITY_CHOICES = [1, 2, 3, 4, 5]
user_rent_data = {}
KALININGRAD_TZ = pytz.timezone('Europe/Kaliningrad')

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# -------- Клавиатуры -------- #

def main_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Арендовать велосипед")],
            [types.KeyboardButton(text="Перезапустить бот"), types.KeyboardButton(text="📞 Поддержка")]
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
            [types.KeyboardButton(text="Начать аренду 🚴🚴🚴...")],
            [types.KeyboardButton(text="Перезапустить бот"), types.KeyboardButton(text="📞 Поддержка")]
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

# Клавиатура во время аренды
def during_rent_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🔴 Завершить аренду")],  # Кнопка для завершения аренды
            [types.KeyboardButton(text="⏱ Сколько времени катаюсь?")],  # Кнопка для времени
            [types.KeyboardButton(text="📞 Поддержка")]  # Кнопка для поддержки
        ],
        resize_keyboard=True
    )

def contact_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True
    )

# -------- Inline клавиатуры -------- #

def confirm_rent_inline():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Подтвердить аренду", callback_data="confirm_rent")],
        [types.InlineKeyboardButton(text="↩️ Вернуться к выбору", callback_data="back_to_cart")]
    ])

def confirm_rent_inline():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Подтвердить аренду", callback_data="confirm_rent")],
        [types.InlineKeyboardButton(text="↩️ Вернуться к выбору", callback_data="back_to_cart")]
    ])

# -------- Функция для записи аренды в статистику -------- #

def save_rent_to_csv(data, duration_min, total_price, period_str):
    file_exists = os.path.isfile("rents.csv")
    with open("rents.csv", "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "user_id", "user_name", "phone", "cart", "minutes", "total_price", "period"
            ])
        writer.writerow([
            data.get("user_id"),
            data.get("user_name"),
            data.get("phone"),
            str(data.get("cart")),
            duration_min,
            total_price,
            period_str
        ])

# -------- Обработчики -------- #

@dp.message(F.text == "/start")
async def greet(message: types.Message):
    try:
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
    except Exception:
        await message.answer(
            "<b>Добро пожаловать в сервис велопроката BalticBike!</b>\n\n"
            "🌊 Прокатитесь по Балтийской косе и побережью на стильных велосипедах!\n"
            "Выберите категорию, добавьте вело в корзину и нажмите <b>«Начать аренду»</b>.\n\n"
            "Желаем приятной поездки! 🚲",
            reply_markup=main_menu_keyboard()
        )

@dp.message(F.text == "/help")
async def help_cmd(message: types.Message):
    await message.answer(
        "<b>ℹ️ Краткая инструкция по боту BalticBike:</b>\n"
        "• <b>/start</b> — начать сначала\n"
        "• <b>/help</b> — справка\n"
        "• <b>/myid</b> — узнать свой ID\n"
        "• <b>/stats</b> — статистика (только для админа)\n"
        "• <b>Арендовать велосипед</b> — начать оформление\n"
        "• <b>📞 Поддержка</b> — связаться с нами\n"
        "• Всё остальное — используйте кнопки ниже!"
    )

@dp.message(F.text == "Перезапустить бот")
async def restart_bot(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if data and data.get("is_renting"):
        await message.answer("❗ Нельзя перезапустить бот во время активной аренды. Сначала завершите аренду!")
        return
    keyboard = main_menu_keyboard()
    await message.answer(
        "Бот успешно перезапущен!\n\n"
        "Нажмите «Арендовать велосипед», чтобы начать оформление.",
        reply_markup=keyboard
    )

@dp.message(F.text == "📞 Поддержка")
async def support(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)

    # Если аренда активна, показываем клавиатуру аренды, иначе просто информацию о поддержке
    if data and data.get("is_renting"):
        # Если аренда активна, показываем клавиатуру с кнопками для аренды
        await message.answer(
            SUPPORT_TEXT,
            reply_markup=during_rent_keyboard()  # Клавиатура с аренды
        )
    else:
        # Если аренда не активна, показываем общую информацию
        await message.answer(
            SUPPORT_TEXT,
            reply_markup=main_menu_keyboard()  # Основное меню без кнопок аренды
        )



@dp.message(F.text == "⏱ Сколько времени катаюсь?")
async def time_spent(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)

    if data and data.get("is_renting"):
        # Рассчитываем время, которое прошло с начала аренды
        start_time = data["start_time"]
        end_time = datetime.now(KALININGRAD_TZ)
        duration = end_time - start_time
        minutes = int(duration.total_seconds() // 60)

        # Если прошло меньше часа, показываем в минутах
        if minutes < 60:
            time_str = f"{minutes} мин"
        else:
            hours = minutes // 60
            minutes_left = minutes % 60
            time_str = f"{hours} ч {minutes_left} мин"

        await message.answer(
            f"⏱ Вы катаетесь уже {time_str}.",
            reply_markup=during_rent_keyboard()
        )
    else:
        await message.answer(
            "Ошибка! Вы не начали аренду или аренда уже завершена.",
            reply_markup=main_menu_keyboard()
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
    # Показываем фото, если файл есть
    img_path = bike_categories[cat_name]["img"]
    if os.path.exists(img_path):
        await message.answer_photo(
            FSInputFile(img_path),
            caption=f"Вы выбрали: {bike_categories[cat_name]['emoji']} <b>{cat_name}</b>\nЦена: {bike_categories[cat_name]['hour']}₽/час\n\nСколько добавить в корзину?",
            reply_markup=qty_keyboard
        )
    else:
        await message.answer(
            f"Вы выбрали: {bike_categories[cat_name]['emoji']} <b>{cat_name}</b>\nЦена: {bike_categories[cat_name]['hour']}₽/час\n\nСколько добавить в корзину?",
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
        await message.answer("Пожалуйста, выберите количество только из кнопок ниже!")
        return
    cat = data["last_category"]
    data["cart"][cat] = data["cart"].get(cat, 0) + qty
    data["awaiting_quantity"] = False
    data["last_category"] = None
    keyboard = categories_keyboard()
    await message.answer(
        f"Добавлено {qty} |{cat}| велосипед(а).\n\n"
        "Добавьте ещё и нажмите <b>«Начать аренду»</b>.",
        reply_markup=keyboard
    )

@dp.message(F.text == "Посмотреть корзину")
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if not data or not data["cart"]:
        await message.answer("Ваша корзина пуста! Добавьте велосипеды для аренды.", reply_markup=categories_keyboard())
        return
    cart_str = "\n".join([
        f"{bike_categories[cat]['emoji']} <b>{cat}</b>: {cnt} шт. ({bike_categories[cat]['hour']}₽/ч)"
        for cat, cnt in data["cart"].items()
    ])
    total_hour_price = sum([bike_categories[cat]['hour'] * cnt for cat, cnt in data["cart"].items()])
    await message.answer(
        f"В вашей корзине:\n{cart_str}\n━━━━━━━━━━━━━━━━━━━━\n<b>Общая стоимость за 1 час: {total_hour_price}₽</b>",
        reply_markup=cart_keyboard()
    )

@dp.message(F.text == "Очистить корзину")
async def clear_cart(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_rent_data:
        user_rent_data[user_id]["cart"] = {}
        user_rent_data[user_id]["is_renting"] = False
        user_rent_data[user_id]["start_time"] = None
    keyboard = categories_keyboard()
    await message.answer("Корзина очищена! Можете выбрать велосипеды снова.", reply_markup=keyboard)


@dp.message(F.text == "Начать аренду 🚴🚴🚴...")
async def start_rent_preview(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)

    if not data or not data["cart"]:
        await message.answer("Сначала выберите хотя бы один велосипед.")
        return

    cart_str = "\n".join([
        f"{bike_categories[cat]['emoji']} <b>{cat}</b>: {cnt} шт. ({bike_categories[cat]['hour']}₽/ч)"
        for cat, cnt in data["cart"].items()
    ])

    total_hour_price = sum([bike_categories[cat]['hour'] * cnt for cat, cnt in data["cart"].items()])

    # Убираем клавиатуру при нажатии "Начать аренду"
    await message.answer(
        "Вы начали оформление аренды. Пожалуйста, подождите...",
        reply_markup=types.ReplyKeyboardRemove()  # Убираем клавиатуру
    )

    await message.answer(
        "Прежде чем поехать, проверьте велосипед и убедитесь, что всё работает:\n"
        "- Тормоза и шины.\n"
        "- Сиденье под ваш рост.\n\n"
        "<b><u>Теперь соблюдайте эти простые правила безопасности:</u></b>\n"
        "- <b>Будьте внимательны!</b> Следите за дорогой.\n"
        "- <b>Не гоните!</b> Наслаждайтесь поездкой.\n"
        "- <b>Не перегружайте велосипед.</b> Удобство важнее.\n"
        "- <b>Осторожно на подъёмах и спусках.</b> Дороги могут быть неровными.\n"
        "- <b>Берегите велосипед.</b> Возвращайте его в хорошем состоянии.\n\n"

    )

    # Отправляем информацию о заказе
    await message.answer(
        f"Вы выбрали:\n{cart_str}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>💸 Стоимость за 1 час: {total_hour_price} руб.</b>\n\n"
        "Нажмите «Подтвердить аренду», чтобы начать, или вернитесь к выбору.",
        reply_markup=confirm_rent_inline()  # Кнопка подтверждения аренды
    )

@dp.callback_query(F.data == "back_to_cart")
async def back_to_cart(callback: types.CallbackQuery):
    # Убираем только кнопки "Подтвердить аренду" и "Вернуться к выбору"
    await callback.message.edit_reply_markup(reply_markup=None)

    # Показываем корзину снова
    user_id = callback.from_user.id
    data = user_rent_data.get(user_id)

    if not data or not data["cart"]:
        await callback.message.answer("Ваша корзина пуста! Добавьте велосипеды для аренды.", reply_markup=categories_keyboard())
        return

    cart_str = "\n".join([f"{bike_categories[cat]['emoji']} <b>{cat}</b>: {cnt} шт. ({bike_categories[cat]['hour']}₽/ч)" for cat, cnt in data["cart"].items()])
    total_hour_price = sum([bike_categories[cat]['hour'] * cnt for cat, cnt in data["cart"].items()])

    await callback.message.answer(
        f"В вашей корзине:\n{cart_str}\n━━━━━━━━━━━━━━━━━━━━\n<b>Общая стоимость за 1 час: {total_hour_price}₽</b>",
        reply_markup=cart_keyboard()  # Возвращаем клавиатуру корзины
    )

@dp.callback_query(F.data == "confirm_rent")
async def confirm_rent_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_rent_data.get(user_id)

    if not data:
        await callback.message.answer("Ошибка! Начните оформление заново.")
        return

    if not data["phone"] and not data["asked_phone"]:
        data["asked_phone"] = True
        await callback.message.answer("Пожалуйста, отправьте свой номер телефона кнопкой ниже для оформления аренды.", reply_markup=contact_keyboard())
        await callback.answer()
        return

    # Убираем только кнопки "Подтвердить аренду" и "Вернуться к выбору"
    await callback.message.edit_reply_markup(reply_markup=None)

    # Запускаем процесс аренды
    await start_rent_real(callback.message)
    await callback.answer()

async def start_rent_real(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data[user_id]
    data["start_time"] = datetime.now(KALININGRAD_TZ)
    data["is_renting"] = True
    keyboard = during_rent_keyboard()
    cart_str = "\n".join([
        f"{bike_categories[cat]['emoji']} <b>{cat}</b>: {cnt} шт. ({bike_categories[cat]['hour']}₽/ч)"
        for cat, cnt in data["cart"].items()
    ])

    total_hour_price = sum([bike_categories[cat]['hour'] * qty for cat, qty in data["cart"].items()])

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

@dp.message(F.text == "🔴 Завершить аренду")
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
        f"Вы катаетесь {minutes} минут(ы) на:\n"
        + "\n".join(lines) +
        "\n━━━━━━━━━━━━━━━━━━━━"
        f"\n<b>💰 Общая стоимость: <u>{total_price} руб.</u></b>\n\n"
        "<b>💸 Оплата аренды по СБП</b>\n"
        f"Переведите сумму на номер:\n"
        f"<code>{PHONE_NUMBER}</code> <u>Сбербанк</u>\n"
        "Нажмите на номер, чтобы скопировать его.\n"
        "После оплаты покажите чек сотруднику или отправьте его в аккаунт поддержки.",
        reply_markup=keyboard
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

    # --- Запись статистики ---
    save_rent_to_csv({
        "user_id": user_id,
        "user_name": message.from_user.full_name,
        "phone": data.get("phone", ""),
        "cart": data["cart"]
    }, minutes, total_price, period_str)

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
    await start_rent_real(message)

@dp.message(F.text == "/myid")
async def my_id(message: types.Message):
    await message.answer(f"Ваш user_id: {message.from_user.id}")

@dp.message(F.text == "/stats")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    try:
        with open("rents.csv", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
    except FileNotFoundError:
        await message.answer("Пока нет данных о прокатах.")
        return

    total_rents = len(reader)
    today = date.today().isoformat()
    today_rents = [row for row in reader if today in row["period"]]
    today_count = len(today_rents)

    bikes_counter = Counter()
    total_income = 0
    total_minutes = 0

    for row in reader:
        cart = eval(row["cart"])
        for cat, qty in cart.items():
            bikes_counter[cat] += int(qty)
        total_income += int(row["total_price"])
        total_minutes += int(row["minutes"])

    most_popular = bikes_counter.most_common(1)
    popular_bike = most_popular[0][0] if most_popular else "Нет данных"
    avg_minutes = total_minutes // total_rents if total_rents else 0

    await message.answer(
        f"📊 <b>Статистика проката</b>\n"
        f"Всего завершённых прокатов: <b>{total_rents}</b>\n"
        f"Прокатов сегодня: <b>{today_count}</b>\n"
        f"Самый популярный велик: <b>{popular_bike}</b>\n"
        f"Общая выручка: <b>{total_income} руб.</b>\n"
        f"Среднее время аренды: <b>{avg_minutes} мин</b>"
    )

# --- Показываем время аренды, если аренда активна --- #
@dp.message(lambda m: m.from_user.id in user_rent_data and user_rent_data[m.from_user.id].get("is_renting"))
async def status_time_active(message: types.Message):
    user_id = message.from_user.id
    data = user_rent_data.get(user_id)
    if data and data.get("is_renting"):
        duration = datetime.now(KALININGRAD_TZ) - data["start_time"]
        minutes = int(duration.total_seconds() // 60)
        await message.answer(
            f"⏱ Сейчас ваша аренда продолжается уже {minutes} мин.\n"
            "Нажмите 'Завершить аренду', когда закончите кататься.",
            reply_markup=during_rent_keyboard()
        )

# --- Общий обработчик на случайный текст --- #
@dp.message()
async def fallback(message: types.Message):
    await message.answer(
        "Пожалуйста, пользуйтесь кнопками ниже 👇\n"
        "Так оформление пройдёт быстрее и без ошибок!"
    )

# -------- Запуск -------- #
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
