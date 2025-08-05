import asyncio
import time
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes
import threading
import http.server
import socketserver


def fake_web_server():
    PORT = 10000
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server at port {PORT}")
        httpd.serve_forever()

# Start the fake server in another thread
threading.Thread(target=fake_web_server, daemon=True).start()

# === CONFIGURATION ===
BOT_TOKEN = "8468578455:AAGJYZptIyD8RRq4S6gejzKOE51nYyck7No"
DELETE_DELAY = 20  # in seconds (default)
auto_delete_enabled = True
message_buffer = []

# === LOGGER SETUP ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
log = logging.getLogger()

# === HANDLERS ===
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

async def delete_old_messages(bot):
    global message_buffer
    while True:
        current_time = time.time()
        to_delete = []

        for msg in message_buffer:
            if current_time - msg['timestamp'] >= DELETE_DELAY:
                to_delete.append(msg)

        for msg in to_delete:
            try:
                await bot.delete_message(chat_id=msg['chat_id'], message_id=msg['message_id'])
                log.info(f"✅ Deleted message {msg['message_id']}")
            except Exception as e:
                log.warning(f"❌ Could not delete message {msg['message_id']}: {e}")
            message_buffer.remove(msg)

        await asyncio.sleep(5)  # check every 5 seconds

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

# === STARTUP HOOK ===
async def on_startup(app):
    app.create_task(delete_old_messages(app.bot))
    log.info("🚀 Background cleaner started")

# === MAIN ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("startdelete", startdelete))
    app.add_handler(CommandHandler("stopdelete", stopdelete))
    app.add_handler(CommandHandler("settime", settime))

    log.info("🤖 Bot is running... (Bulk Deletion Mode)")
    app.run_polling()
