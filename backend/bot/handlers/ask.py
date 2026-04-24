from __future__ import annotations

from core.logger import get_logger
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.config import BOT_AGENT_ENABLED
from bot.identity.decorators import require_admin
from bot.identity.store import get_store
from bot.rate_limit import get_ask_limiter

logger = get_logger(__name__)


@require_admin
async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ask <question> — query the WACH AI agent (admin only)."""
    if not BOT_AGENT_ENABLED:
        await update.message.reply_text("🤖 Assistant is currently disabled.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /ask <question>\nExample: /ask why did e0507 fail?")
        return

    question = " ".join(context.args)
    user_id = str(update.effective_user.id)

    limiter = get_ask_limiter()
    if not limiter.is_allowed(user_id):
        await update.message.reply_text("⚠️ Rate limit reached. Try again in a few minutes.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    store = get_store()
    user = store.get_user(user_id)
    role = user.role if user else "admin"

    try:
        from bot.agent.ask import ask
        answer = await ask(question=question, user_id=user_id, role=role)
        if not answer or not isinstance(answer, str):
            raise ValueError(f"Unexpected agent response: {answer!r}")
    except Exception as e:
        logger.warning(f"Agent ask failed: {e}")
        await update.message.reply_text("⚠️ Could not reach the WACH agent. Try again shortly.")
        return

    store.log_audit(
        actor_id=user_id,
        action="ask",
        ticket_no=None,
        details={"question": question[:200]},
    )

    await update.message.reply_text(f"🤖 *WACH Agent*\n\n{answer}", parse_mode="Markdown")


def get_handlers() -> list:
    return [CommandHandler("ask", cmd_ask)]
