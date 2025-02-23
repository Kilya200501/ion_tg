import os
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- Константы состояний (этапов диалога) ---
CHOOSING_CATEGORY, CHOOSING_MODEL, CHOOSING_SERVICE, GETTING_CONTACTS = range(4)

# --- Переменные окружения ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MANAGER_CHAT_ID = os.environ.get("MANAGER_CHAT_ID")  # строка, конвертируем в int при использовании

# --- Список категорий ---
APPLE_CATEGORIES = ["iPhone", "iPad", "Apple Watch", "Macbook"]

# --- Словарь моделей по категориям ---
MODELS_BY_CATEGORY = {
    "iPhone": [
        "IPhone 16 Pro Max", "IPhone 16 Pro", "IPhone 16 Plus", "IPhone 16",
        "IPhone 15 Pro Max", "IPhone 15 Pro", "IPhone 15 Plus", "IPhone 15",
        "IPhone 14 Pro Max", "IPhone 14 Pro", "IPhone 14 Plus", "IPhone 14",
        "IPhone 13 Pro Max", "IPhone 13 Pro", "IPhone 13", "IPhone 13 mini",
        "IPhone 12 Pro Max", "IPhone 12 / 12 Pro", "IPhone 12 mini",
        "IPhone 11 Pro Max", "IPhone 11 Pro", "IPhone 11",
        "IPhone Xs Max", "IPhone Xs", "IPhone X"
    ],
    "iPad": ["iPad Air", "iPad Pro", "iPad Mini"],  # Пример, можно расширить
    "Apple Watch": ["Apple Watch SE", "Apple Watch Ultra"],  # Пример
    "Macbook": ["Macbook Air", "Macbook Pro 14", "Macbook Pro 16"],  # Пример
}

# --- Виды услуг для iPhone ---
IPHONE_SERVICES = [
    "Замена стекла (если трещины)",
    "Полировка стекла (царапины)",
    "Замена дисплея (оригинал )",
    "Замена корпуса (оригинал)",
    "Замена заднего стекла",
    "Замена аккумулятора (оригинал)",
    "Другие услуги ..."
]

# --- Пример услуг для остальных категорий (при желании доработайте) ---
DEFAULT_SERVICES = [
    "Замена экрана",
    "Замена батареи",
    "Диагностика",
    "Ремонт кнопок"
]

# --- Утилитная функция для сборки inline-клавиатуры из списка строк ---
def build_inline_keyboard(labels):
    """
    Принимает список labels (строк) и возвращает InlineKeyboardMarkup
    с одной кнопкой в строке (callback_data = label).
    """
    buttons = [[InlineKeyboardButton(label, callback_data=label)] for label in labels]
    return InlineKeyboardMarkup(buttons)

# --- Шаг 1. Команда /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Приветствие и показ списка категорий.
    """
    await update.message.reply_text(
        "Привет! Я бот по ремонту техники Apple.\n"
        "Выберите категорию, чтобы узнать о видах услуг:"
    )
    # Генерируем клавиатуру для выбора категории
    reply_markup = build_inline_keyboard(APPLE_CATEGORIES)
    await update.message.reply_text(
        text="Пожалуйста, выберите категорию:",
        reply_markup=reply_markup
    )
    return CHOOSING_CATEGORY

# --- Шаг 2. Выбор категории ---
async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Пользователь выбрал категорию (например, iPhone).
    Сохраняем выбор и выводим модели из MODELS_BY_CATEGORY.
    """
    query = update.callback_query
    await query.answer()  # подтверждаем нажатие
    category = query.data
    context.user_data["category"] = category

    # Получаем список моделей для выбранной категории:
    models = MODELS_BY_CATEGORY.get(category, ["Неизвестная категория"])

    reply_markup = build_inline_keyboard(models)
    await query.edit_message_text(
        text=f"Вы выбрали: {category}.\nТеперь выберите модель:",
        reply_markup=reply_markup
    )
    return CHOOSING_MODEL

# --- Шаг 3. Выбор модели ---
async def model_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Пользователь выбрал модель. Сохраняем модель.
    Далее предлагаем список услуг (для iPhone - IPHONE_SERVICES, иначе DEFAULT_SERVICES).
    """
    query = update.callback_query
    await query.answer()
    model = query.data
    context.user_data["model"] = model

    # Если выбрана категория iPhone - показываем iPhone-услуги
    category = context.user_data["category"]
    if category == "iPhone":
        services = IPHONE_SERVICES
    else:
        services = DEFAULT_SERVICES

    reply_markup = build_inline_keyboard(services)
    await query.edit_message_text(
        text=f"Вы выбрали: {model}.\nТеперь выберите услугу:",
        reply_markup=reply_markup
    )
    return CHOOSING_SERVICE

# --- Шаг 4. Выбор услуги ---
async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Пользователь выбрал конкретную услугу. Сохраняем и просим контакты (телефон и пр.).
    """
    query = update.callback_query
    await query.answer()
    service = query.data
    context.user_data["service"] = service

    text_for_user = (
        f"Отлично! Вы выбрали:\n"
        f"- Категория: {context.user_data['category']}\n"
        f"- Модель: {context.user_data['model']}\n"
        f"- Услуга: {context.user_data['service']}\n\n"
        "Пожалуйста, оставьте свои контактные данные, чтобы наш менеджер мог связаться с вами.\n"
        "Например: ваше имя, номер телефона и удобное время для звонка."
    )

    # Редактируем предыдущее сообщение, убирая клавиатуру, и просим контакты:
    await query.edit_message_text(text=text_for_user)
    return GETTING_CONTACTS

# --- Шаг 5. Получаем контакты от пользователя ---
async def get_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Принимаем текст от пользователя как его контактные данные,
    отправляем заявку менеджеру, показываем кнопку «Связаться с менеджером».
    """
    contacts = update.message.text
    context.user_data["contacts"] = contacts

    category = context.user_data["category"]
    model = context.user_data["model"]
    service = context.user_data["service"]

    user_id = update.message.from_user.id
    username = update.message.from_user.username or "(нет username)"

    # Отправляем менеджеру уведомление о заявке, если настроен MANAGER_CHAT_ID
    if MANAGER_CHAT_ID:
        try:
            manager_id = int(MANAGER_CHAT_ID)
            details = (
                f"Новая заявка!\n\n"
                f"Пользователь: @{username} (ID: {user_id})\n"
                f"Категория: {category}\n"
                f"Модель: {model}\n"
                f"Услуга: {service}\n"
                f"Контакты: {contacts}"
            )
            await context.bot.send_message(chat_id=manager_id, text=details)
        except ValueError:
            logging.warning("MANAGER_CHAT_ID не является числом или не задан.")
        except Exception as e:
            logging.error(f"Ошибка при отправке менеджеру: {e}")

    # Кнопка «Связаться с менеджером»
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Связаться с менеджером",
                url="https://t.me/managerusername"  # Замените на реальную ссылку/username
            )
        ]
    ])

    await update.message.reply_text(
        "Спасибо! Ваша заявка отправлена.\nНаш менеджер скоро свяжется с вами.",
        reply_markup=reply_markup
    )

    # Завершаем диалог
    return ConversationHandler.END

# --- Отмена диалога /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Досрочная отмена оформления заявки командой /cancel.
    """
    await update.message.reply_text(
        "Оформление заявки прервано.\nЕсли захотите начать заново, отправьте /start.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    """
    Точка входа в программу: создаём приложение, регистрируем ConversationHandler и запускаем poll.
    """
    # Создаём приложение с токеном
    application = Application.builder().token(BOT_TOKEN).build()

    # Определяем ConversationHandler с этапами диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(category_chosen)],
            CHOOSING_MODEL: [CallbackQueryHandler(model_chosen)],
            CHOOSING_SERVICE: [CallbackQueryHandler(service_chosen)],
            GETTING_CONTACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contacts)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Запускаем бота (long-polling)
    application.run_polling()

if __name__ == "__main__":
    main()
