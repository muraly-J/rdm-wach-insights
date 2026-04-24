from __future__ import annotations

"""
bot/identity/registration.py
─────────────────────────────
ConversationHandler for user registration.

Flow (DM only):
  1. User sends /register or /start (unregistered)
  2. Bot shows role picker: [🔧 Technician] [👔 Admin/Manager]
  3. User taps role → bot asks for display name (ForceReply)
  4. User replies with name → bot creates pending user + notifies admin group
  5. Admin taps [✅ Approve] or [❌ Reject] on the registration card
"""

from core.logger import get_logger
from telegram import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import ADMIN_CHAT_ID
from bot.identity.store import get_store

logger = get_logger(__name__)

# Conversation states
SELECT_ROLE = 0
ENTER_NAME = 1

# Context keys
_REG_ROLE_KEY = "reg_role"


# ── Registration ConversationHandler ───────────────────────────────────────────

async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: show role picker."""
    if update.effective_chat.type != "private":
        await update.message.reply_text("📩 Please DM me to register.")
        return ConversationHandler.END

    store = get_store()
    existing = store.get_user(str(update.effective_user.id))

    if existing:
        if existing.status == "active":
            await update.message.reply_text(
                f"✅ You're already registered as *{existing.role}*.",
                parse_mode="Markdown",
            )
            return ConversationHandler.END
        elif existing.status == "pending":
            await update.message.reply_text(
                "⏳ Your registration is pending admin approval."
            )
            return ConversationHandler.END
        elif existing.status == "disabled":
            await update.message.reply_text(
                "🚫 Your account is disabled. Contact an admin."
            )
            return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔧 Technician", callback_data="register_role:technician"),
            InlineKeyboardButton("👔 Admin/Manager", callback_data="register_role:admin"),
        ]
    ])
    await update.message.reply_text(
        "👋 Welcome! Let's get you registered.\n\nSelect your role:",
        reply_markup=keyboard,
    )
    return SELECT_ROLE


async def cb_select_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User tapped a role button."""
    query = update.callback_query
    await query.answer()

    role = query.data.split(":")[1]
    context.user_data[_REG_ROLE_KEY] = role

    role_label = "Technician" if role == "technician" else "Admin/Manager"
    await query.edit_message_text(
        f"You selected: *{role_label}*\n\nWhat's your display name?",
        parse_mode="Markdown",
    )
    # Use ForceReply to prompt for name
    await query.message.reply_text(
        "Type your name:",
        reply_markup=ForceReply(selective=True),
    )
    return ENTER_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User replied with their display name."""
    display_name = update.message.text.strip()
    if not display_name or len(display_name) > 100:
        await update.message.reply_text("❌ Name must be 1–100 characters. Try again:")
        return ENTER_NAME

    role = context.user_data.get(_REG_ROLE_KEY, "technician")
    user_id = str(update.effective_user.id)
    username = update.effective_user.username

    store = get_store()

    # Create pending user
    store.create_user(
        user_id=user_id,
        telegram_username=username,
        display_name=display_name,
        role=role,
    )

    # Audit
    store.log_audit(
        actor_id=user_id,
        action="register",
        details={"role": role, "display_name": display_name},
    )

    await update.message.reply_text(
        f"✅ Registration submitted!\n\n"
        f"*Name:* {display_name}\n"
        f"*Role:* {role}\n\n"
        f"⏳ Waiting for admin approval. You'll be notified when approved.",
        parse_mode="Markdown",
    )

    # Notify admin group
    if ADMIN_CHAT_ID:
        role_label = "Technician" if role == "technician" else "Admin/Manager"
        at_user = f"@{username}" if username else f"ID:{user_id}"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"reg_approve:{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reg_reject:{user_id}"),
            ]
        ])
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"👋 *New Registration*\n\n"
                f"{at_user} wants *{role_label}*\n"
                f"Display name: {display_name}\n"
                f"Telegram ID: `{user_id}`"
            ),
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    return ConversationHandler.END


async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel registration."""
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END


# ── Approval callbacks (handled in admin group) ───────────────────────────────

async def cb_reg_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin taps Approve on a registration card."""
    query = update.callback_query
    user_id = query.data.split(":")[1]
    admin_id = str(query.from_user.id)
    admin_name = query.from_user.username or query.from_user.first_name or admin_id

    store = get_store()

    # Check if admin is actually an admin
    admin_user = store.get_user(admin_id)
    if not admin_user or admin_user.role != "admin" or admin_user.status != "active":
        await query.answer("You're not an admin.", show_alert=True)
        return

    # Check if user is still pending
    target = store.get_user(user_id)
    if not target:
        await query.answer("User not found.", show_alert=True)
        return
    if target.status == "active":
        await query.answer(f"Already approved by {target.approved_by}.", show_alert=True)
        return
    if target.status == "disabled":
        await query.answer("User was rejected.", show_alert=True)
        return

    success = store.approve_user(user_id, approved_by=admin_id)
    if not success:
        await query.answer("Could not approve.", show_alert=True)
        return

    await query.answer("✅ Approved!")

    # Update the card
    await query.edit_message_text(
        f"✅ *Registration Approved*\n\n"
        f"{target.display_name} ({target.role})\n"
        f"Approved by @{admin_name}",
        parse_mode="Markdown",
    )

    # Audit
    store.log_audit(
        actor_id=admin_id,
        action="approve_registration",
        details={"target_user_id": user_id, "role": target.role},
    )

    # DM the approved user
    try:
        role_label = "Technician" if target.role == "technician" else "Admin/Manager"
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"🎉 You're approved as *{role_label}*!\n\n"
                f"Tap /help to see available commands."
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Could not DM approved user {user_id}: {e}")


async def cb_reg_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin taps Reject on a registration card."""
    query = update.callback_query
    user_id = query.data.split(":")[1]
    admin_id = str(query.from_user.id)
    admin_name = query.from_user.username or query.from_user.first_name or admin_id

    store = get_store()

    # Check if admin
    admin_user = store.get_user(admin_id)
    if not admin_user or admin_user.role != "admin" or admin_user.status != "active":
        await query.answer("You're not an admin.", show_alert=True)
        return

    target = store.get_user(user_id)
    if not target:
        await query.answer("User not found.", show_alert=True)
        return
    if target.status != "pending":
        await query.answer(f"User is already {target.status}.", show_alert=True)
        return

    success = store.reject_user(user_id)
    if not success:
        await query.answer("Could not reject.", show_alert=True)
        return

    await query.answer("❌ Rejected.")

    await query.edit_message_text(
        f"❌ *Registration Rejected*\n\n"
        f"{target.display_name} ({target.role})\n"
        f"Rejected by @{admin_name}",
        parse_mode="Markdown",
    )

    # Audit
    store.log_audit(
        actor_id=admin_id,
        action="reject_registration",
        details={"target_user_id": user_id, "role": target.role},
    )

    # DM the rejected user
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text="❌ Your registration was not approved. Contact an admin if you think this is an error.",
        )
    except Exception as e:
        logger.warning(f"Could not DM rejected user {user_id}: {e}")


# ── Handler registration ──────────────────────────────────────────────────────

def get_handlers() -> list:
    """Return all registration-related handlers."""
    register_conv = ConversationHandler(
        entry_points=[CommandHandler("register", cmd_register)],
        states={
            SELECT_ROLE: [
                CallbackQueryHandler(cb_select_role, pattern=r"^register_role:(technician|admin)$"),
            ],
            ENTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
            ],
        },
        fallbacks=[CommandHandler("cancel", reg_cancel)],
        conversation_timeout=300,
    )
    return [
        register_conv,
        CallbackQueryHandler(cb_reg_approve, pattern=r"^reg_approve:\d+$"),
        CallbackQueryHandler(cb_reg_reject, pattern=r"^reg_reject:\d+$"),
    ]
