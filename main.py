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

# Состояния диалога
CHOOSING_CATEGORY, CHOOSING_MODEL, CHOOSING_SERVICE, GETTING_CONTACTS = range(4)

# Переменные окружения (BOT_TOKEN и MANAGER_CHAT_ID)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MANAGER_CHAT_ID = os.environ.get("MANAGER_CHAT_ID")

# Списки моделей
IPHONE_MODELS = [
    "IPhone 16 Pro Max", "IPhone 16 Pro", "IPhone 16 Plus", "IPhone 16",
    "IPhone 15 Pro Max", "IPhone 15 Pro", "IPhone 15 Plus", "IPhone 15",
    "IPhone 14 Pro Max", "IPhone 14 Pro", "IPhone 14 Plus", "IPhone 14",
    "IPhone 13 Pro Max", "IPhone 13 Pro", "IPhone 13", "IPhone 13 mini",
    "IPhone 12 Pro Max", "IPhone 12 / 12 Pro", "IPhone 12 mini",
    "IPhone 11 Pro Max", "IPhone 11 Pro", "IPhone 11",
    "IPhone Xs Max", "IPhone Xs", "IPhone X"
]

IPAD_MODELS = [
    "iPad Pro 13",
    "iPad Air 13",
    "iPad Pro 12,9 (2022)",
    "iPad Pro 12,9 (2021)",
    "iPad Pro 12,9 (2020)",
    "iPad Pro 12,9 (2018)",
    "iPad Air 11 (2024)",
    "iPad Pro Pro 11 (2024)",
    "iPad Pro 11 (2022)",
    "iPad Pro 11 (2021)",
    "iPad Pro 11 (2020)",
    "iPad Pro 11 (2018)",
    "iPad Pro 10.5",
    "iPad Pro 9,7",
    "iPad mini 6",
    "iPad mini 4 / mini 5",
    "iPad Air 5",
    "iPad Air 4",
    "iPad Air 3/2",
    "iPad 7 / 8 / 9",
]

AWATCH_MODELS = [
    "Apple Watch Ultra 2",
    "Apple Watch Ultra",
    "Apple Watch Series 10",
    "Apple Watch Series 9",
    "Apple Watch Series 8",
    "Apple Watch Series 7",
    "Apple Watch Series 6",
    "Apple Watch Series 5/Se",
    "Apple Watch Series 4",
    "Apple Watch Series 3/2/1"
]

# Списки услуг
IPHONE_SERVICES = [
    "Диагностика",
    "Замена стекла (если трещины)",
    "Полировка стекла (царапины)",
    "Замена дисплея (оригинал )",
    "Замена корпуса (оригинал)",
    "Замена заднего стекла",
    "Замена аккумулятора (оригинал)",
    "Другие услуги ...",
    "Связаться с менеджером"
]

IPAD_SERVICES = [
    "Диагностика",
    "Замена стекла(если трещины)",
    "Замена сенсора",
    "Замена дисплея (оригинал )",
    "Замена корпуса (оригинал )",
    "Выпрямление корпуса",
    "Замена аккумулятора (оригинал)",
    "Другие  услуги",
 "Связаться с менеджером"
]

AWATCH_SERVICES = [
    "Диагностика",
    "Замена стекла (только трещины)",
    "Замена сенсора / стекла",
    "Полировка стекла (царапины)",
    "Дисплея (оригинал )",
    "Замена аккумулятора (оригинал)",
    "Другие  услуги"
 "Связаться с менеджером",
]

# Главный словарь с данными по категориям
# Если "models" или "services" = None, этап пропускается
CATEGORIES = {
    "iPhone": {
        "models": IPHONE_MODELS,
        "services": IPHONE_SERVICES
    },
    "iPad": {
        "models": IPAD_MODELS,
        "services": IPAD_SERVICES
    },
    "Apple Watch": {
        "models": AWATCH_MODELS,
        "services": AWATCH_SERVICES
    },
    "Macbook": {
        "models": None,    # Пропускаем выбор модели
        "services": None,  # Пропускаем выбор услуг
    }
}

def build_inline_keyboard(labels):
    """
    Строит InlineKeyboardMarkup из списка строк,
    по одной кнопке на строку (callback_data = label).
    """
    if not labels:
        return None  # Если список пуст, вернём None
    buttons = [[InlineKeyboardButton(label, callback_data=label)] for label in labels]
    return InlineKeyboardMarkup(buttons)

# --- Шаг 1. /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Приветствие + выбор категории.
    """
    welcome_text = (
        "Добрый день! Вас приветствует ion-service — "
        "специализированный сервис по ремонту техники Apple.\n"
        "Мы поможем быстро и качественно решить вашу проблему.\n\n"
        "Для начала, выберите категорию устройства:"
    )
    await update.message.reply_text(welcome_text)

    categories_list = list(CATEGORIES.keys())  # ["iPhone", "iPad", "Apple Watch", "Macbook"]
    reply_markup = build_inline_keyboard(categories_list)
    await update.message.reply_text(
        text="Пожалуйста, выберите категорию:",
        reply_markup=reply_markup
    )
    return CHOOSING_CATEGORY

# --- Шаг 2. Пользователь выбрал категорию ---
async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохранить выбор категории. Если у категории нет 'models',
    сразу переходим к запросу контактов (пропуская модель/услуги).
    Иначе предлагаем выбрать модель.
    """
    query = update.callback_query
    await query.answer()
    category = query.data
    context.user_data["category"] = category

    cat_info = CATEGORIES.get(category)
    if not cat_info:
        # На случай, если что-то некорректное
        await query.edit_message_text(text="Неизвестная категория.")
        return ConversationHandler.END

    # Если нет списка моделей (как у Macbook) -> пропускаем шаги выбора модели и услуг
    if cat_info["models"] is None:
        # Для наглядности сохраним 'model'/'service' как «N/A»
        context.user_data["model"] = "N/A"
        context.user_data["service"] = "N/A"

        # Просим сразу контактные данные
        text_for_user = (
            f"Вы выбрали: {category}.\n"
            "Нет списка моделей/услуг для этой категории.\n"
            "Пожалуйста, опишите, что хотите отремонтировать, и оставьте контактные данные.\n"
            "Например: Имя, номер телефона.\n"
            "Подсказка: Если хотите \"Заказать звонок менеджера\", "
            "просто напишите об этом и укажите номер."
        )
        await query.edit_message_text(text=text_for_user)
        return GETTING_CONTACTS

    # Иначе есть модели -> переходим к шагу CHOOSING_MODEL
    models = cat_info["models"]
    reply_markup = build_inline_keyboard(models)
    await query.edit_message_text(
        text=f"Вы выбрали: {category}.\nТеперь выберите модель:",
        reply_markup=reply_markup
    )
    return CHOOSING_MODEL

# --- Шаг 3. Выбор модели ---
async def model_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Если у категории нет 'services', сразу переходим к контактам.
    Иначе предлагаем список услуг.
    """
    query = update.callback_query
    await query.answer()
    chosen_model = query.data
    context.user_data["model"] = chosen_model

    category = context.user_data["category"]
    cat_info = CATEGORIES.get(category)

    if not cat_info or cat_info["services"] is None:
        # Пропускаем услуги
        context.user_data["service"] = "N/A"

        text_for_user = (
            f"Вы выбрали: {chosen_model}.\n"
            "Нет отдельного списка услуг для данной категории.\n"
            "Пожалуйста, укажите ваши контактные данные."
        )
        await query.edit_message_text(text=text_for_user)
        return GETTING_CONTACTS

    # Иначе у категории есть список услуг -> предлагаем их
    services = cat_info["services"]
    reply_markup = build_inline_keyboard(services)
    await query.edit_message_text(
        text=f"Вы выбрали: {chosen_model}.\nТеперь выберите услугу:",
        reply_markup=reply_markup
    )
    return CHOOSING_SERVICE

# --- Шаг 4. Выбор услуги ---
async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняем услугу, просим контактную информацию.
    """
    query = update.callback_query
    await query.answer()
    chosen_service = query.data
    context.user_data["service"] = chosen_service

    text_for_user = (
        f"Отличный выбор!\n"
        f"- Категория: {context.user_data['category']}\n"
        f"- Модель: {context.user_data['model']}\n"
        f"- Услуга: {context.user_data['service']}\n\n"
        "Теперь нам нужны ваши контактные данные.\n"
        "Пожалуйста, укажите имя и номер телефона (либо удобный способ связи)."
    )

    await query.edit_message_text(text=text_for_user)
    return GETTING_CONTACTS

# --- Шаг 5. Получаем контакты ---
async def get_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Финальный шаг: пользователь присылает контакты.
    Отправляем менеджеру всю информацию, завершаем диалог.
    """
    contacts = update.message.text
    context.user_data["contacts"] = contacts

    category = context.user_data["category"]
    model = context.user_data["model"]
    service = context.user_data["service"]

    user_id = update.message.from_user.id
    username = update.message.from_user.username or "(не указан)"

    if MANAGER_CHAT_ID:
        try:
            manager_id = int(MANAGER_CHAT_ID)
            details = (
                "Новая заявка!\n\n"
                f"Пользователь: @{username} (ID: {user_id})\n"
                f"Категория: {category}\n"
                f"Модель: {model}\n"
                f"Услуга: {service}\n"
                f"Контакты (сообщение от пользователя): {contacts}\n"
            )
            await context.bot.send_message(chat_id=manager_id, text=details)
        except ValueError:
            logging.warning("MANAGER_CHAT_ID не является числом или не задан.")
        except Exception as e:
            logging.error(f"Ошибка при отправке менеджеру: {e}")

    farewell_text = (
        "Спасибо! Ваша заявка принята.\n"
        "Мы свяжемся с вами в ближайшее время.\n\n"
        "Чтобы начать новую заявку, введите /start.\n"
        "С уважением, ion-service."
    )

    await update.message.reply_text(farewell_text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Если пользователь вводит /cancel, прерываем диалог.
    """
    await update.message.reply_text(
        "Заявка прервана. Если потребуется снова начать, введите /start.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler
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
    application.run_polling()

if __name__ == "__main__":
    main()
