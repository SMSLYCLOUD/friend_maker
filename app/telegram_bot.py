import asyncio
import logging
from typing import Set, Optional

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from app.config import settings

logger = logging.getLogger("TelegramBot")

INTERNAL_API = "http://localhost:8000"
VNC_BASE_URL = "http://153.75.247.117:6080"


class TelegramBot:
    def __init__(self, token: str, allowed_user_ids: Set[int] = None):
        self.token = token
        self.allowed_user_ids = allowed_user_ids or set()
        self.app: Application | None = None
        self._http = httpx.AsyncClient(timeout=15)
        self._poll_task: asyncio.Task | None = None

    async def start(self):
        if not self.token:
            logger.info("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
            return

        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("analytics", self.cmd_analytics))
        self.app.add_handler(CommandHandler("campaign", self.cmd_campaign))
        self.app.add_handler(CommandHandler("startcampaign", self.cmd_start_campaign))
        self.app.add_handler(CommandHandler("stopcampaign", self.cmd_stop_campaign))
        self.app.add_handler(CommandHandler("resume", self.cmd_resume))
        self.app.add_handler(CommandHandler("skip", self.cmd_skip))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))

        await self.app.initialize()
        await self.app.start()
        self._poll_task = asyncio.create_task(self._run_polling())
        logger.info("Telegram bot started")

    async def _run_polling(self):
        try:
            await self.app.updater.start_polling()
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")

    async def stop(self):
        if self._poll_task:
            self._poll_task.cancel()
        if self.app:
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            except Exception as e:
                logger.warning(f"Telegram stop error: {e}")
        await self._http.aclose()
        logger.info("Telegram bot stopped")

    def _is_allowed(self, user_id: int) -> bool:
        if not self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids

    async def _api(self, method: str, path: str, json=None):
        url = f"{INTERNAL_API}{path}"
        headers = {"X-API-Key": settings.API_KEY, "Content-Type": "application/json"}
        resp = await self._http.request(method, url, headers=headers, json=json)
        resp.raise_for_status()
        return resp.json()

    async def _reply(self, update: Update, text: str, markdown: bool = True):
        kw = {"parse_mode": "Markdown"} if markdown else {}
        await update.message.reply_text(text, **kw)

    # ── Proactive messaging ──────────────────────────────────────────

    async def send_message(self, text: str, markdown: bool = True, reply_markup=None):
        """Send a proactive message to all allowed users."""
        if not self.app or not self.allowed_user_ids:
            return
        kw = {"parse_mode": "Markdown"} if markdown else {}
        if reply_markup:
            kw["reply_markup"] = reply_markup
        for user_id in self.allowed_user_ids:
            try:
                await self.app.bot.send_message(user_id, text, **kw)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")

    async def send_blocker_alert(self, campaign, blocker):
        """Send a blocker alert with inline keyboard buttons."""
        vnc_url = f"{VNC_BASE_URL}"
        campaign_id = campaign.id
        short_id = campaign_id[:12]

        text = (
            f"🚨 *Campaign Blocked*\n\n"
            f"*Campaign:* {campaign.name} (`{short_id}...`)\n"
            f"*Platform:* {getattr(campaign, 'platform', 'N/A')}\n"
            f"*Blocker:* {blocker.blocker_type}\n"
            f"*Detail:* {blocker.message}\n"
        )
        if blocker.url:
            text += f"*URL:* {blocker.url}\n"
        text += (
            f"\n👉 *Fix via VNC:* {vnc_url}\n\n"
            f"Once you've resolved the issue, click *Resume* or type `/resume {short_id}`"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Resume", callback_data=f"resume:{campaign_id}"),
                InlineKeyboardButton("⏭ Skip Target", callback_data=f"skip:{campaign_id}"),
            ],
            [
                InlineKeyboardButton("🛑 Stop Campaign", callback_data=f"stop:{campaign_id}"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.send_message(text, reply_markup=reply_markup)

    # ── Callback query handler ───────────────────────────────────────

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not self._is_allowed(query.from_user.id):
            await query.answer("Not authorized.", show_alert=True)
            return

        data = query.data or ""
        if ":" not in data:
            await query.answer("Invalid action.")
            return

        action, campaign_id = data.split(":", 1)

        try:
            if action == "resume":
                await self._api("POST", f"/api/campaigns/{campaign_id}/resume")
                await query.edit_message_text(
                    f"✅ Campaign `{campaign_id[:12]}...` resumed.\n"
                    f"Waiting for next action..."
                )
            elif action == "skip":
                await self._api("POST", f"/api/campaigns/{campaign_id}/skip-blocker")
                await query.edit_message_text(
                    f"⏭ Campaign `{campaign_id[:12]}...` — blocker skipped.\n"
                    f"Continuing with next target..."
                )
            elif action == "stop":
                await self._api("POST", f"/api/campaigns/{campaign_id}/stop")
                await query.edit_message_text(
                    f"🛑 Campaign `{campaign_id[:12]}...` stopped."
                )
            else:
                await query.answer("Unknown action.")
                return

            await query.answer()
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await query.answer(f"Error: {e}", show_alert=True)

    # ── Commands ─────────────────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user.id):
            return
        await self._reply(update,
            "🤖 *SocialGrowthAI Bot*\n\n"
            "*/status* — Campaign & account overview\n"
            "*/analytics* — Action statistics\n"
            "*/startcampaign* `<id>` — Start a campaign\n"
            "*/stopcampaign* `<id>` — Stop a campaign\n"
            "*/resume* `<id>` — Resume a blocked campaign\n"
            "*/skip* `<id>` — Skip blocker and continue\n"
            "*/help* — This message"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_start(update, context)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user.id):
            return
        try:
            campaigns, accounts = await asyncio.gather(
                self._api("GET", "/api/campaigns"),
                self._api("GET", "/api/accounts"),
            )
            lines = ["📊 *Campaigns*"]
            for c in campaigns:
                status_emoji = "🚧" if c["status"] == "blocked" else "🟢" if c["status"] == "active" else "⏸"
                lines.append(f"{status_emoji} `{c['id'][:8]}...` {c['name']}: *{c['status']}*")
            if not campaigns:
                lines.append("  _(none)_")
            lines.append("")
            lines.append(f"👤 *Accounts:* {len(accounts)} configured")
            await self._reply(update, "\n".join(lines))
        except Exception as e:
            logger.error(f"Status error: {e}")
            await self._reply(update, f"❌ Error: {e}")

    async def cmd_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user.id):
            return
        try:
            data = await self._api("GET", "/api/analytics/summary")
            await self._reply(update,
                f"📈 *Analytics*\n\n"
                f"Total actions: `{data['total_actions']}`\n"
                f"Today: `{data['today_actions']}`\n"
                f"Success rate: `{data['success_rate']}%`"
            )
        except Exception as e:
            await self._reply(update, f"❌ Error: {e}")

    async def cmd_campaign(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_status(update, context)

    async def cmd_start_campaign(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user.id):
            return
        if not context.args:
            await self._reply(update, "Usage: `/startcampaign <campaign_id>`")
            return
        campaign_id = context.args[0]
        try:
            await self._api("POST", f"/api/campaigns/{campaign_id}/start")
            await self._reply(update, f"✅ Campaign `{campaign_id[:8]}...` started")
        except Exception as e:
            await self._reply(update, f"❌ Error: {e}")

    async def cmd_stop_campaign(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user.id):
            return
        if not context.args:
            await self._reply(update, "Usage: `/stopcampaign <campaign_id>`")
            return
        campaign_id = context.args[0]
        try:
            await self._api("POST", f"/api/campaigns/{campaign_id}/stop")
            await self._reply(update, f"✅ Campaign `{campaign_id[:8]}...` stopped")
        except Exception as e:
            await self._reply(update, f"❌ Error: {e}")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user.id):
            return
        if not context.args:
            await self._reply(update, "Usage: `/resume <campaign_id>`")
            return
        campaign_id = context.args[0]
        try:
            await self._api("POST", f"/api/campaigns/{campaign_id}/resume")
            await self._reply(update, f"✅ Campaign `{campaign_id[:8]}...` resumed")
        except Exception as e:
            await self._reply(update, f"❌ Error: {e}")

    async def cmd_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user.id):
            return
        if not context.args:
            await self._reply(update, "Usage: `/skip <campaign_id>`")
            return
        campaign_id = context.args[0]
        try:
            await self._api("POST", f"/api/campaigns/{campaign_id}/skip-blocker")
            await self._reply(update, f"⏭ Campaign `{campaign_id[:8]}...` — blocker skipped")
        except Exception as e:
            await self._reply(update, f"❌ Error: {e}")


_bot_instance: TelegramBot | None = None


def get_bot_instance() -> Optional[TelegramBot]:
    """Return the running bot instance (for proactive messaging)."""
    return _bot_instance


async def start_bot():
    global _bot_instance
    allowed = set()
    raw = settings.TELEGRAM_ALLOWED_USER_IDS.strip()
    if raw:
        allowed = {int(x.strip()) for x in raw.split(",") if x.strip()}
    _bot_instance = TelegramBot(settings.TELEGRAM_BOT_TOKEN, allowed)
    await _bot_instance.start()


async def stop_bot():
    global _bot_instance
    if _bot_instance:
        await _bot_instance.stop()
        _bot_instance = None
