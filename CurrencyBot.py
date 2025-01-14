# -*- coding: utf-8 -*-
"""bot.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1rxHQ_IT3wUHwP6wXKXDYJEzTH1fAfcML
"""

pip install python-telegram-bot pandas

pip install python-telegram-bot --upgrade

import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import nest_asyncio

# Применяем nest_asyncio для разрешения запуска бота внутри уже работающего event loop
nest_asyncio.apply()

# Этапы разговора для команды /rate
WAITING_FOR_RATE_DATE = 1
WAITING_FOR_RATE_CURRENCY = 2

# Этапы разговора для команды /convert
WAITING_FOR_CONVERT_DATE = 3
WAITING_FOR_CONVERT_AMOUNT = 4
WAITING_FOR_CONVERT_FROM = 5
WAITING_FOR_CONVERT_TO = 6

# Кастомная ошибка для некорректной будущей даты
class НекорректнаяБудущаяДата(Exception):
    pass

# Функция для проверки даты
def validate_date(date: str) -> None:
    parsed_date = datetime.strptime(date, "%d.%m.%Y")
    if parsed_date > datetime.now():
        raise НекорректнаяБудущаяДата("Эта дата ещё не наступила.")
    if parsed_date.year > 2025 or parsed_date.year < 1992:
        raise ValueError("Год должен быть в диапазоне 1992–2025.")

# Функция для получения курса валют
def exchanger(date: str, cur: str) -> str:
    try:
        # Проверка формата и валидности даты
        validate_date(date)

        # Загрузка данных с сайта ЦБ РФ
        url = f"https://cbr.ru/currency_base/daily/?UniDbQuery.Posted=True&UniDbQuery.To={date}"
        df = pd.read_html(url, thousands='. ', decimal=',')[0]

        # Проверка наличия валюты
        if cur not in df['Букв. код'].to_numpy():
            available_currencies = ", ".join(df['Букв. код'].to_numpy())
            return f"Некорректный код валюты. Доступные валюты: {available_currencies}"

        # Получение курса
        row = df.loc[df['Букв. код'] == cur]
        rate = (row["Курс"] / row["Единиц"]).iloc[0]
        return f"Курс {cur} на {date}: {rate:.2f} руб."
    except НекорректнаяБудущаяДата as e:
        return str(e)
    except ValueError:
        return "Некорректный формат даты. Используйте ДД.ММ.ГГГГ."
    except Exception as e:
        return f"Ошибка при обработке данных: {e}"

# Функция для конвертации валюты
def convert_currency(amount: float, from_currency: str, to_currency: str, date: str) -> str:
    try:
        validate_date(date)
        if from_currency == "RUB" and to_currency != "RUB":
            # Получаем курс для перевода из рубля в целевую валюту
            rate = exchanger(date, to_currency)
            if "Ошибка" in rate:
                return rate
            rate = float(rate.split(":")[1].strip().split()[0])  # Извлекаем курс
            result = round(amount / rate, 2)
            return f"{amount} RUB = {result} {to_currency.upper()}"
        elif to_currency == "RUB" and from_currency != "RUB":
            # Получаем курс для перевода из исходной валюты в рубль
            rate = exchanger(date, from_currency)
            if "Ошибка" in rate:
                return rate
            rate = float(rate.split(":")[1].strip().split()[0])  # Извлекаем курс
            result = round(amount * rate, 2)
            return f"{amount} {from_currency.upper()} = {result} RUB"
        else:
            return f"Невозможно конвертировать между {from_currency.upper()} и {to_currency.upper()}"
    except Exception as e:
        return f"Неверный код валюты"

# Функция для получения списка доступных валют
def get_available_currencies() -> str:
    try:
        # Загружаем текущие данные с сайта ЦБ РФ
        url = "https://cbr.ru/currency_base/daily/"
        df = pd.read_html(url, thousands='. ', decimal=',')[0]

        # Извлекаем список доступных валют
        currencies = df['Букв. код'].to_numpy()
        return f"Доступные валюты: {', '.join(currencies)}"
    except Exception as e:
        return f"Ошибка при получении списка валют: {e}"

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я помогу узнать курс валют и конвертировать валюту. Используйте команды:\n"
        "/available — Посмотреть доступные валюты\n"
        "/rate — Узнать курс валюты на дату\n"
        "/convert — Конвертировать валюту"
    )

# Обработчик команды /available
async def available(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = get_available_currencies()
    await update.message.reply_text(response)

# Остальные обработчики, описанные ранее...
# Код обработки команд /rate и /convert (тот же, что был до этого)

# Главная функция
async def main():
    # Вставьте ваш токен сюда
    TOKEN = "7833948236:AAH_85ShBig9RHNDR20BqClKjMmZdJNoPk0"

    # Создаём приложение
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("available", available))

    # Настройка ConversationHandler для обработки команды /rate
    rate_conversation = ConversationHandler(
        entry_points=[CommandHandler("rate", rate)],
        states={
            WAITING_FOR_RATE_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate),
            ],
            WAITING_FOR_RATE_CURRENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_currency),
            ],
        },
        fallbacks=[],
    )

    # Настройка ConversationHandler для обработки команды /convert
    convert_conversation = ConversationHandler(
        entry_points=[CommandHandler("convert", convert)],
        states={
            WAITING_FOR_CONVERT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_convert_date),
            ],
            WAITING_FOR_CONVERT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_convert_amount),
            ],
            WAITING_FOR_CONVERT_FROM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_convert_from),
            ],
            WAITING_FOR_CONVERT_TO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_convert_to),
            ],
        },
        fallbacks=[],
    )

    # Добавляем обработчики команд
    application.add_handler(rate_conversation)
    application.add_handler(convert_conversation)

    # Запуск бота
    await application.run_polling()

# Запуск бота
await main()