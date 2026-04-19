import os
import random
import re
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiohttp import web

from database import (
    Application,
    init_db,
    create_application,
    get_application,
    get_recent_applications,
    update_application_status,
    get_next_app_id,
)


class Form(StatesGroup):
    comment = State()


INSTRUCTIONS = (
    "При оформлении и направлении заявки просим убедиться в заполнении всех обязательных полей:\n\n"
    "1. Username (никнейм) — для направления документа.\n"
    "2. В комментарии к заявке необходимо указать следующие данные:\n"
    "   · имя (в соответствии с указанным на платформе);\n"
    "   · дата совершения сделки;\n"
    "   · наименование предмета (дисциплины)",
)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[0-9 ()-]{7,}$")


ADMIN_DEFAULT_ID = 1023041853


def parse_admin_ids(env_value: str) -> List[int]:
    """Парсит список админов из строки через запятую."""
    if not env_value:
        return [ADMIN_DEFAULT_ID]
    try:
        return [int(x.strip()) for x in env_value.split(",") if x.strip()]
    except ValueError:
        return [ADMIN_DEFAULT_ID]


SHEETS_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


# In-memory cache for quick lookup (optional, mainly for compatibility)
APPLICATIONS_BY_ID: Dict[int, Application] = {}
_GSHEET = None

# Защита от дублирования: user_id -> timestamp последнего обработанного сообщения
LAST_MESSAGE_TIME: Dict[int, float] = {}
DEBOUNCE_SECONDS = 1.0


def build_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Инструкция")],
        [KeyboardButton(text="Отправить заявку")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)


def build_back_menu() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text="Назад")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)


def build_admin_actions(app_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="Написать пользователю", callback_data=f"admin:reply:{app_id}")
    return kb


def _get_gsheet(sheet_id: str, creds_json_path: str):
    global _GSHEET
    if _GSHEET is not None:
        return _GSHEET

    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json_path, SHEETS_SCOPE)
    client = gspread.authorize(creds)
    _GSHEET = client.open_by_key(sheet_id).sheet1
    return _GSHEET


async def log_application_to_sheets(app: Application, bot: Optional[Bot]) -> None:
    admin_ids = getattr(bot, "_admin_ids", [ADMIN_DEFAULT_ID]) if bot else [ADMIN_DEFAULT_ID]
    # Используем первого админа для уведомлений об ошибках
    admin_id = admin_ids[0] if admin_ids else ADMIN_DEFAULT_ID

    sheet_id = os.getenv("SHEET_ID", "").strip()
    creds_path = os.getenv("GOOGLE_CREDS_JSON", "").strip()
    if not sheet_id or not creds_path:
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"@{app.username}" if app.username else ""
    row = [ts, str(app.user_id), username, app.comment]

    try:
        await asyncio.to_thread(lambda: _get_gsheet(sheet_id, creds_path).append_row(row))
    except Exception as e:
        print(f"[ERROR] Google Sheets append_row failed: {e}")
        try:
            if bot is not None:
                await bot.send_message(admin_id, f"[WARN] Не удалось записать заявку в Google Sheets: {e}")
        except Exception:
            pass


def format_instruction() -> str:
    return random.choice(INSTRUCTIONS)


def format_application_for_admin(app: Application) -> str:
    uname = f"@{app.username}" if app.username else "(без username)"
    return (
        "Новая заявка\n"
        f"ID: {app.app_id}\n"
        f"Статус: {app.status}\n"
        f"User: {app.user_id} {uname}\n"
        f"Комментарий: {app.comment}"
    )




def should_skip_update(user_id: int) -> bool:
    now = time.time()
    last = LAST_MESSAGE_TIME.get(user_id, 0)
    if now - last < DEBOUNCE_SECONDS:
        return True
    LAST_MESSAGE_TIME[user_id] = now
    return False


async def cmd_start(message: Message, state: FSMContext) -> None:
    if message.from_user is None or should_skip_update(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "Выберите действие:",
        reply_markup=build_main_menu(),
    )


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if message.from_user is None or should_skip_update(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "Ок, отменено.",
        reply_markup=build_main_menu(),
    )


async def cmd_admin(message: Message, bot: Bot, admin_ids: List[int]) -> None:
    if message.from_user is None or message.from_user.id not in admin_ids or should_skip_update(message.from_user.id):
        return

    recent = get_recent_applications(10)
    if not recent:
        await message.answer("Заявок пока нет")
        return

    # Показываем в обратном порядке (самые новые сверху)
    text = "Последние заявки:\n" + "\n".join(
        f"{a.app_id} | {a.status} | @{a.username or 'no-username'} | {a.comment[:30]}{'...' if len(a.comment) > 30 else ''}"
        for a in recent
    )
    await message.answer(text)


async def on_text_message(message: Message, state: FSMContext) -> None:
    if message.from_user is None or should_skip_update(message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text:
        return

    # Если пользователь в процессе ввода комментария — игнорируем (пусть on_comment обработает)
    current_state = await state.get_state()
    if current_state == Form.comment:
        return

    if text == "Инструкция":
        await state.clear()
        await message.answer(
            format_instruction(),
            reply_markup=build_back_menu(),
        )
        return

    if text == "Отправить заявку":
        await state.clear()
        await message.answer("Напишите ваш комментарий:")
        await state.set_state(Form.comment)
        return

    if text == "Назад":
        await state.clear()
        await message.answer(
            "Выберите действие:",
            reply_markup=build_main_menu(),
        )
        return

    # Неизвестная команда — показываем подсказку
    await message.answer(
        "Используйте кнопки меню:",
        reply_markup=build_main_menu(),
    )


async def on_admin_action(query: CallbackQuery, bot: Bot, admin_ids: List[int], dp: Dispatcher) -> None:
    # Функционал ответа пользователю временно отключён по запросу
    if query.from_user.id not in admin_ids:
        await query.answer("Недостаточно прав", show_alert=True)
        return
    await query.answer("Отключено")


async def on_comment(message: Message, state: FSMContext) -> None:
    if message.from_user is None or should_skip_update(message.from_user.id):
        return
    comment = (message.text or "").strip()
    if not comment:
        await message.answer("Комментарий не может быть пустым. Напишите комментарий:")
        return

    # Получаем username
    username = message.from_user.username or ""

    # Создаем заявку в базе данных
    app = create_application(
        user_id=message.from_user.id,
        username=username,
        comment=comment
    )
    # Кэшируем для быстрого доступа
    APPLICATIONS_BY_ID[app.app_id] = app

    # Очищаем состояние FSM после создания заявки
    await state.clear()

    await message.answer(
        "Готово. Ваш комментарий:\n"
        f"{comment}\n\n"
        "Если нужно — можете отправить ещё одну заявку через меню."
    )

    bot: Optional[Bot] = message.bot
    await log_application_to_sheets(app, bot)
    if bot is not None:
        admin_ids = getattr(bot, "_admin_ids", [ADMIN_DEFAULT_ID])
        # Отправляем заявку всем админам
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    format_application_for_admin(app),
                )
                print(f"[INFO] Заявка #{app.app_id} отправлена админу {admin_id}")
            except Exception as e:
                print(f"[ERROR] Не удалось отправить заявку админу {admin_id}: {e}")

    await message.answer(
        "Выберите действие:",
        reply_markup=build_main_menu(),
    )


async def main() -> None:
    # Инициализируем базу данных
    init_db()

    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    admin_ids = parse_admin_ids(os.getenv("ADMIN_ID", ""))

    bot = Bot(token=token)
    bot._admin_ids = admin_ids  # type: ignore[attr-defined]
    dp = Dispatcher()

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_cancel, Command("cancel"))
    dp.message.register(lambda m, b=bot: cmd_admin(m, b, admin_ids), Command("admin"))

    dp.callback_query.register(lambda q, b=bot: on_admin_action(q, b, admin_ids, dp), F.data.startswith("admin:"))

    dp.message.register(on_comment, Form.comment)

    dp.message.register(on_text_message, F.text)

    # Check required environment variables
    if not token:
        print("ERROR: BOT_TOKEN not set!")
        return
    if not admin_ids:
        print("WARNING: ADMIN_ID not set!")

    await bot.delete_webhook(drop_pending_updates=True)
    print(f"Bot started. Admins: {admin_ids}")

    # HTTP server for Render Web Service (keeps the service awake)
    async def health_check(request):
        return web.Response(text="Bot is running!")

    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP server started on port {port}")

    await dp.start_polling(bot, polling_timeout=5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
