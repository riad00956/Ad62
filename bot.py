
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, Filters, MessageHandler
from telegram.error import BadRequest

# Use environment variable or fallback token (hardcoded)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7685134552:AAH_qlJp65O9w7Vkzq74J_w6BmoJWguuWrY')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_warnings = {}

def is_admin(user_id, chat):
    member = chat.get_member(user_id)
    return member.status in ['administrator', 'creator']

def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Welcome to the Admin Bot!\nUse /panel in group to manage users easily.")

def panel(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type != 'supergroup':
        return update.message.reply_text("ℹ️ This command only works in supergroups.")

    if not is_admin(user.id, chat):
        return update.message.reply_text("🚫 You must be an admin to use this.")

    buttons = [
        [InlineKeyboardButton("🚫 Ban", callback_data="ban"),
         InlineKeyboardButton("👢 Kick", callback_data="kick")],
        [InlineKeyboardButton("🔇 Mute", callback_data="mute"),
         InlineKeyboardButton("🔊 Unmute", callback_data="unmute")],
        [InlineKeyboardButton("⚠️ Warn", callback_data="warn"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    update.message.reply_text("🔧 *Admin Panel*\nReply to a user's message and choose an action:",
                              reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    chat = update.effective_chat

    query.answer()
    context.user_data['last_action'] = query.data
    query.edit_message_text(f"✅ Now reply to a message to perform: *{query.data.upper()}*", parse_mode="Markdown")

def handle_reply(update: Update, context: CallbackContext):
    chat = update.effective_chat
    admin = update.effective_user
    replied_user = update.message.reply_to_message.from_user
    target_id = replied_user.id
    action = context.user_data.get('last_action')

    if not is_admin(admin.id, chat):
        return update.message.reply_text("🚫 Admins only!")

    if action == "ban":
        try:
            chat.kick_member(target_id)
            update.message.reply_text(f"🚫 Banned {replied_user.full_name}")
        except BadRequest:
            update.message.reply_text("❌ Cannot ban this user.")
    elif action == "kick":
        try:
            chat.unban_member(target_id)
            update.message.reply_text(f"👢 Kicked {replied_user.full_name}")
        except BadRequest:
            update.message.reply_text("❌ Cannot kick this user.")
    elif action == "mute":
        try:
            chat.restrict_member(user_id=target_id, permissions=ChatPermissions(can_send_messages=False))
            update.message.reply_text(f"🔇 Muted {replied_user.full_name}")
        except BadRequest:
            update.message.reply_text("❌ Cannot mute.")
    elif action == "unmute":
        try:
            chat.restrict_member(
                user_id=target_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            update.message.reply_text(f"🔊 Unmuted {replied_user.full_name}")
        except BadRequest:
            update.message.reply_text("❌ Cannot unmute.")
    elif action == "warn":
        count = user_warnings.get(target_id, 0) + 1
        user_warnings[target_id] = count
        update.message.reply_text(f"⚠️ Warned {replied_user.full_name} ({count}/3)")
        if count >= 3:
            try:
                chat.kick_member(target_id)
                update.message.reply_text(f"🚫 Auto-banned {replied_user.full_name} for 3 warnings.")
                user_warnings[target_id] = 0
            except BadRequest:
                update.message.reply_text("❌ Cannot auto-ban.")
    elif action == "stats":
        count = user_warnings.get(target_id, 0)
        update.message.reply_text(f"📊 {replied_user.full_name} has {count} warning(s).")
    else:
        update.message.reply_text("❗ Unknown action. Use /panel first.")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("panel", panel))
    dp.add_handler(CallbackQueryHandler(handle_buttons))
    dp.add_handler(MessageHandler(Filters.reply & Filters.text & Filters.group, handle_reply))

    # Webhook (for Render)
    PORT = int(os.environ.get('PORT', 8443))
    updater.start_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=BOT_TOKEN
    )
    updater.bot.set_webhook(f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}")
    updater.idle()

if __name__ == "__main__":
    main()
