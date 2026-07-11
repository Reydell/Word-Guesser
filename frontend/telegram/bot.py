from .config import (
    ALLOWED_USERS,
    API_BASE_URL,
    BOT_TOKEN,
    BOT_USERNAME,
    DEBOUNCE_SECONDS,
)
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import httpx


# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('I want to play a game with you.\n\nType /newgame to play.')
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
        /newgame to play
        
        The goal is to guess the secret word by asking questions. If you feel completely stuck, ask for a hint.
        """)

async def newgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/games/",
            timeout=10
        )
        try:
            response.raise_for_status()
        except:
            await update.message.reply_text("Sorry the server is down!")
            return

    data = response.json()
    context.chat_data['game_id'] = data['game_id']

    await update.message.reply_text(data['message'])


# Responses
async def send_debounced_reply(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await asyncio.sleep(DEBOUNCE_SECONDS)

    pending_texts = context.chat_data.pop("pending_texts", [])
    if not pending_texts:
        return
    
    combined_text = "\n".join(pending_texts)
    response = await handle_response(context, combined_text)

    await context.bot.send_message(chat_id=chat_id, text=response)

async def handle_response(context: ContextTypes.DEFAULT_TYPE, text: str) -> str:
    game_id = context.chat_data.get('game_id', None)

    if game_id is None:
        return 'Type /newgame to start a game.'
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/games/{game_id}/messages",
            json={"message": text},
            timeout=10,
        )
        response.raise_for_status()

    data = response.json()
    return data['message']

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    if update.message.chat.username not in ALLOWED_USERS:
        return

    if message_type == 'group':
        if BOT_USERNAME not in text:
            return
        text = text.replace(BOT_USERNAME, "").strip()
        if not text:
            return
        
    context.chat_data.setdefault("pending_texts", []).append(text)
    old_task = context.chat_data.get("reply_task")
    if old_task and not old_task.done():
        old_task.cancel()

    context.chat_data["reply_task"] = asyncio.create_task(
        send_debounced_reply(context, update.effective_chat.id)
    )
    

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('newgame', newgame_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    print("READY")
    app.run_polling(poll_interval=3)
