import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from telegram.error import BadRequest

# Bot token from environment or fallback
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7685134552:AAH_qlJp65O9w7Vkzq74J_w6BmoJWguuWrY')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_warnings = {}

async def is_admin(user_id, chat):
    member = await chat.get_member(user_id)
    return member.status in ['administrator', 'creator']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the Admin Bot!\nUse /panel in group to manage users easily.")

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type != 'supergroup':
        return await update.message.reply_text("ℹ️ This command only works in supergroups.")

    if not await is_admin(user.id, chat):
        return await update.message.reply_text("🚫 You must be an admin to use this.")

    buttons = [
        [InlineKeyboardButton("🚫 Ban", callback_data="ban"),
         InlineKeyboardButton("👢 Kick", callback_data="kick")],
        [InlineKeyboardButton("🔇 Mute", callback_data="mute"),
         InlineKeyboardButton("🔊 Unmute", callback_data="unmute")],
        [InlineKeyboardButton("⚠️ Warn", callback_data="warn"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    await update.message.reply_text(
        "🔧 *Admin Panel*\nReply to a user's message and choose an action:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['last_action'] = query.data
    await query.edit_message_text(f"✅ Now reply to a message to perform: *{query.data.upper()}*", parse_mode="Markdown")

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    admin = update.effective_user
    replied_user = update.message.reply_to_message.from_user
    target_id = replied_user.id
    action = context.user_data.get('last_action')

    if not await is_admin(admin.id, chat):
        return await update.message.reply_text("🚫 Admins only!")

    try:
        if action == "ban":
            await chat.ban_member(target_id)
            await update.message.reply_text(f"🚫 Banned {replied_user.full_name}")
        elif action == "kick":
            await chat.unban_member(target_id)
            await update.message.reply_text(f"👢 Kicked {replied_user.full_name}")
        elif action == "mute":
            await chat.restrict_member(user_id=target_id, permissions=ChatPermissions(can_send_messages=False))
            await update.message.reply_text(f"🔇 Muted {replied_user.full_name}")
        elif action == "unmute":
            await chat.restrict_member(
                user_id=target_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            await update.message.reply_text(f"🔊 Unmuted {replied_user.full_name}")
        elif action == "warn":
            count = user_warnings.get(target_id, 0) + 1
            user_warnings[target_id] = count
            await update.message.reply_text(f"⚠️ Warned {replied_user.full_name} ({count}/3)")
            if count >= 3:
                await chat.ban_member(target_id)
                await update.message.reply_text(f"🚫 Auto-banned {replied_user.full_name} for 3 warnings.")
                user_warnings[target_id] = 0
        elif action == "stats":
            count = user_warnings.get(target_id, 0)
            await update.message.reply_text(f"📊 {replied_user.full_name} has {count} warning(s).")
        else:
            await update.message.reply_text("❗ Unknown action. Use /panel first.")
    except BadRequest as e:
        await update.message.reply_text(f"❌ Error: {e.message}")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT & filters.ChatType.GROUPS, handle_reply))

    # Webhook setup for Render
    PORT = int(os.environ.get('PORT', 8443))
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    )
    await app.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
