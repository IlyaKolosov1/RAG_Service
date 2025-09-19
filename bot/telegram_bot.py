from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, File
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import time
import dotenv
import os
dotenv.load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
AUDIT_URL = os.getenv("AUDIT_URL", "http://audit:8000/log")

def send_log(service: str, level: str, message: str, extra: dict = None):
    payload = {
        "service": service,
        "level": level.upper(),
        "message": message,
    }
    if extra:
        payload.update(extra)

    try:
        requests.post(AUDIT_URL, json=payload, timeout=2)
    except Exception as e:
        # если аудитор недоступен — не ломаем основной сервис
        print(f"[AUDIT ERROR] Ошибка: {e}")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для работы с Yandex GPT. Просто напиши мне свой вопрос"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/process",
            json={"user_id": str(update.effective_user.id), "text": user_message}
        )
        answer = response.json().get("answer")
        await update.message.reply_text(answer)
    except Exception as e:
        send_log("bot", "ERROR", f"Bot error: {str(e)}", {"user_msg": user_message})
        await update.message.reply_text("Ошибка обработки запроса.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    send_log("bot", "ERROR", f"Bot error: {str(context.error)}", {"user_msg": update})
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )

def main():
    """Основная функция"""
    try:
        # Проверяем возможность генерации токена при запуске

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        send_log("bot", "INFO", "Бот запускается")
        application.run_polling()

    except Exception as e:
        send_log("bot", "ERROR", f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
