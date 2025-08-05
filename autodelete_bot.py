import asyncio
import logging
import time
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes
from aiohttp import web

# === CONFIGURATION ===
BOT_TOKEN = "8468578455:AAGJYZptIyD8RRq4S6gejzKOE51nYyck7No"
DELETE_DELAY = 20
auto_delete_enabled = True
message_buffer = []

# === LOGGER SETUP ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
log = logging.getLogger()

# === MESSAGE HANDLER ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_buffer, auto_delete_enabled

    if not auto_delete_enabled:
        return

    message = update.effective_message
    message_info = {
        'chat_id': message.chat_id,
        'message_id': message.message_id,
        'timestamp': time.time()
    }
    message_buffer.append(message_info)
    log.info(f"📩 Message {message.message_id} queued for deletion in {DELETE_DELAY} sec")

# === DELETER ===
async def delete_old_messages(bot):
    global message_buffer
    while True:
        current_time = time.time()
        to_delete = [msg for msg in message_buffer if current_time - msg['timestamp'] >= DELETE_DELAY]

        for msg in to_delete:
            try:
                await bot.delete_message(chat_id=msg['chat_id'], message_id=msg['message_id'])
                log.info(f"✅ Deleted message {msg['message_id']}")
            except Exception as e:
                log.warning(f"❌ Could not delete message {msg['message_id']}: {e}")
            message_buffer.remove(msg)

        await asyncio.sleep(5)

# === COMMANDS ===
async def startdelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_delete_enabled
    auto_delete_enabled = True
    await update.message.reply_text("✅ Auto-delete enabled.")
    log.info("🟢 Auto-delete turned ON")

async def stopdelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_delete_enabled
    auto_delete_enabled = False
    await update.message.reply_text("🛑 Auto-delete disabled.")
    log.info("🔴 Auto-delete turned OFF")

async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DELETE_DELAY
    try:
        seconds = int(context.args[0])
        DELETE_DELAY = seconds
        await update.message.reply_text(f"⏱ Auto-delete time set to {seconds} seconds.")
        log.info(f"🔧 DELETE_DELAY updated to {seconds} seconds")
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Usage: /settime <seconds>")

# === WEB SERVER ===
async def handle_root(request):
    return web.Response(text="✅ Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    log.info(f"🌐 Fake web server running on port {port}")

# === MAIN ===
async def main():
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    telegram_app.add_handler(CommandHandler("startdelete", startdelete))
    telegram_app.add_handler(CommandHandler("stopdelete", stopdelete))
    telegram_app.add_handler(CommandHandler("settime", settime))

    log.info("🤖 Bot is running...")

    # Initialize and start the bot manually (to avoid asyncio.run conflict)
    await telegram_app.initialize()
    await telegram_app.start()
    telegram_app.create_task(delete_old_messages(telegram_app.bot))
    await telegram_app.updater.start_polling()

    # Run bot and web server concurrently
    await start_web_server()

    # Keep running forever
    await telegram_app.updater.wait()

if __name__ == "__main__":
    asyncio.run(main())
