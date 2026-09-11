import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==== ЗАПОЛНИ ЭТИ ДВЕ СТРОКИ ====
import os
TOKEN = os.environ.get("TELEGRAM_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))  # Узнаешь свой ID командой /myid в боте, потом впишешь сюда
# =================================

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

CATEGORIES = {
    "walls": {"name": "🧱 Стены", "works": [
        ("Демонтаж обоев", 3, "м²"),
        ("Штукатурка стен", 15, "м²"),
        ("Шпаклёвка стен", 8, "м²"),
        ("Поклейка обоев", 7, "м²"),
        ("Покраска стен", 5, "м²"),
    ]},
    "floor": {"name": "🧱 Пол", "works": [
        ("Демонтаж покрытия", 4, "м²"),
        ("Стяжка пола", 18, "м²"),
        ("Укладка ламината", 12, "м²"),
        ("Укладка плитки", 25, "м²"),
        ("Установка плинтуса", 3, "м.п."),
    ]},
    "ceiling": {"name": "🧱 Потолок", "works": [
        ("Покраска потолка", 6, "м²"),
        ("Натяжной потолок", 20, "м²"),
        ("Гипсокартонный потолок", 28, "м²"),
    ]},
    "electric": {"name": "⚡ Электрика", "works": [
        ("Замена розетки", 15, "шт"),
        ("Замена выключателя", 12, "шт"),
        ("Прокладка проводки", 8, "м.п."),
        ("Установка люстры", 25, "шт"),
    ]},
    "plumbing": {"name": "🚿 Сантехника", "works": [
        ("Замена смесителя", 30, "шт"),
        ("Установка унитаза", 80, "шт"),
        ("Установка ванны", 150, "шт"),
        ("Установка раковины", 70, "шт"),
    ]},
    "other": {"name": "🧹 Прочее", "works": [
        ("Вывоз мусора", 80, "фикс"),
        ("Уборка после ремонта", 5, "м²"),
    ]},
}

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧮 Рассчитать стоимость")],
        [KeyboardButton(text="📋 Список работ")],
        [KeyboardButton(text="📞 Связаться")],
    ],
    resize_keyboard=True
)

class Calc(StatesGroup):
    choosing_cat = State()
    choosing_works = State()
    entering_quantity = State()
    confirming = State()
    entering_name = State()
    entering_phone = State()

def categories_kb():
    rows = []
    for key, cat in CATEGORIES.items():
        rows.append([InlineKeyboardButton(text=cat["name"], callback_data=f"cat:{key}")])
    rows.append([InlineKeyboardButton(text="✔️ Готово, посчитать", callback_data="finish")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def works_kb(cat_key, selected):
    cat = CATEGORIES[cat_key]
    rows = []
    for i, (name, price, unit) in enumerate(cat["works"]):
        mark = "✅ " if i in selected else "▫️ "
        rows.append([InlineKeyboardButton(
            text=f"{mark}{name} — {price} €/{unit}",
            callback_data=f"work:{cat_key}:{i}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ К категориям", callback_data="back_cats")])
    rows.append([InlineKeyboardButton(text="✔️ Готово, посчитать", callback_data="finish")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        "Я помогу прикинуть стоимость ремонта квартиры в Клайпеде.\n\n"
        "Что хочешь сделать?",
        reply_markup=main_menu
    )

@dp.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(f"Твой Telegram ID: {message.from_user.id}")

@dp.message(F.text == "🧮 Рассчитать стоимость")
async def start_calc(message: Message, state: FSMContext):
    await state.set_state(Calc.choosing_cat)
    await state.update_data(selected={})
    await message.answer("Выбери категорию работ:", reply_markup=categories_kb())

@dp.message(F.text == "📋 Список работ")
async def show_works_list(message: Message):
    text = "📋 Список работ и цены:\n\n"
    for key, cat in CATEGORIES.items():
        text += f"{cat['name']}\n"
        for name, price, unit in cat["works"]:
            text += f"  • {name} — {price} €/{unit}\n"
        text += "\n"
    await message.answer(text)

@dp.message(F.text == "📞 Связаться")
async def contact(message: Message):
    await message.answer("Связь с мастером: @твой_телеграм")

@dp.callback_query(F.data == "back_cats")
async def back_cats(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Calc.choosing_cat)
    await cb.message.edit_text("Выбери категорию работ:", reply_markup=categories_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith("cat:"))
async def open_cat(cb: CallbackQuery, state: FSMContext):
    cat_key = cb.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected", {})
    sel_in_cat = selected.get(cat_key, [])
    await state.set_state(Calc.choosing_works)
    await state.update_data(current_cat=cat_key)
    await cb.message.edit_text(
        f"{CATEGORIES[cat_key]['name']}\nОтметь нужные работы:",
        reply_markup=works_kb(cat_key, sel_in_cat)
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("work:"))
async def toggle_work(cb: CallbackQuery, state: FSMContext):
    _, cat_key, idx_str = cb.data.split(":")
    idx = int(idx_str)
    data = await state.get_data()
    selected = data.get("selected", {})
    sel_in_cat = selected.get(cat_key, [])
    if idx in sel_in_cat:
        sel_in_cat.remove(idx)
    else:
        sel_in_cat.append(idx)
    selected[cat_key] = sel_in_cat
    await state.update_data(selected=selected)
    await cb.message.edit_reply_markup(reply_markup=works_kb(cat_key, sel_in_cat))
    await cb.answer()

@dp.callback_query(F.data == "finish")
async def finish_selection(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", {})
    items = []
    for cat_key, idxs in selected.items():
        for i in idxs:
            name, price, unit = CATEGORIES[cat_key]["works"][i]
            items.append({"name": name, "price": price, "unit": unit, "qty": None})

    if not items:
        await cb.answer("Ты ничего не выбрал!", show_alert=True)
        return

    await state.update_data(items=items, current_item=0)
    await state.set_state(Calc.entering_quantity)
    first = items[0]
    await cb.message.edit_text(
        f"Сколько нужно: {first['name']} ({first['unit']})?\n"
        f"Напиши число, например: 25"
    )
    await cb.answer()

@dp.message(Calc.entering_quantity)
async def enter_quantity(message: Message, state: FSMContext):
    try:
        qty = float(message.text.replace(",", "."))
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, напиши число больше нуля. Например: 25")
        return

    data = await state.get_data()
    items = data["items"]
    current = data["current_item"]
    items[current]["qty"] = qty

    next_idx = current + 1
    if next_idx < len(items):
        await state.update_data(items=items, current_item=next_idx)
        nxt = items[next_idx]
        await message.answer(f"Сколько нужно: {nxt['name']} ({nxt['unit']})?\nНапиши число.")
    else:
        text = "📋 Твоя смета:\n\n"
        total = 0
        for it in items:
            s = it["price"] * it["qty"]
            total += s
            text += f"{it['name']}: {it['qty']} {it['unit']} × {it['price']} € = {s:.0f} €\n"
        text += f"\n💰 Итого примерно: {total:.0f} €\n\n"
        text += "Это предварительный расчёт. Точную цену мастер назовёт после осмотра.\n\n"
        text += "Оставить заявку?"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оставить заявку", callback_data="confirm_yes")],
            [InlineKeyboardButton(text="❌ Не надо", callback_data="confirm_no")],
        ])
        await state.update_data(items=items)
        await state.set_state(Calc.confirming)
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "confirm_no")
async def confirm_no(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Хорошо, если что — я тут.")
    await cb.answer()

@dp.callback_query(F.data == "confirm_yes")
async def confirm_yes(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Calc.entering_name)
    await cb.message.edit_text("Как тебя зовут?")
    await cb.answer()

@dp.message(Calc.entering_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Calc.entering_phone)
    await message.answer("Оставь номер телефона для связи:")

@dp.message(Calc.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    items = data["items"]
    name = data["name"]
    phone = message.text

    text = "🔔 Новая заявка!\n\n"
    text += f"Имя: {name}\n"
    text += f"Телефон: {phone}\n"
    text += f"Telegram: @{message.from_user.username or message.from_user.first_name}\n\n"
    text += "Смета:\n"
    total = 0
    for it in items:
        s = it["price"] * it["qty"]
        total += s
        text += f"• {it['name']}: {it['qty']} {it['unit']} × {it['price']} € = {s:.0f} €\n"
    text += f"\n💰 Итого: {total:.0f} €"

    if OWNER_ID:
        try:
            await bot.send_message(OWNER_ID, text)
        except Exception as e:
            print(f"Ошибка отправки владельцу: {e}")

    await message.answer(
        "Спасибо! Заявка отправлена. Мастер свяжется с тобой в течение дня.",
        reply_markup=main_menu
    )
    await state.clear()

async def main():
    print("Бот запущен.")
    await dp.start_polling(bot)
# --- Код для Render (веб-сервер) ---
from flask import Flask, jsonify
import os
import threading

# Этот блок нужен, чтобы Render видел, что сервис работает.
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

def run_flask():
    # Render сам назначает порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    # host='0.0.0.0' обязателен, чтобы сервер был доступен снаружи
    app.run(host='0.0.0.0', port=port)

# Запускаем Flask-сервер в отдельном потоке, чтобы он не мешал боту
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()
# --- Конец кода для Render ---
if __name__ == "__main__":
    asyncio.run(main())
