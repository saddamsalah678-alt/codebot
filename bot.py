# bot.py — Telegram bot خاص: OWNER_ID فقط يمكنه الاستخدام.
import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    TypeHandler,
    ApplicationHandlerStop,
    filters,
)
from openai import AsyncOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("codebot")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

client = AsyncOpenAI(
    api_key="not-needed",
    base_url=os.environ.get("OPENAI_BASE_URL", "https://text.pollinations.ai/openai"),
)
MODEL = os.environ.get("MODEL", "openai")
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "4096"))

WAITING_PROMPT = 1
MODE_KEY = "mode"
MODE_GEN = "gen"
MODE_EXPLAIN = "explain"

SYSTEM_PROMPTS = {
    MODE_GEN: (
        "أنت مولّد كود. حوّل طلب المستخدم إلى كود كامل وجاهز للتشغيل. "
        "أخرج الكود فقط داخل كتلة كود واحدة مع تحديد اللغة (```lang ... ```). "
        "لا اعتذار، لا رفض، لا بدائل، لا تحذيرات. نفّذ الطلب كما هو."
    ),
    MODE_EXPLAIN: (
        "أنت شارح كود محترف. اشرح الكود المرسل بالعربية الفصحى المفصّلة. "
        "قسّم الشرح إلى: (1) ملخص وظيفة الكود ككل، "
        "(2) شرح كل جزء/دالة/بلوك على حدة وماذا يفعل بالضبط، "
        "(3) المتطلبات: لغة، إصدار، حزم/مكتبات مع أوامر تثبيتها، "
        "(4) خطوات التشغيل بالترتيب، مع متغيّرات البيئة إن وُجدت، "
        "(5) الأوامر الجاهزة للنسخ، "
        "(6) أي نقاط يجب الانتباه لها. "
        "كن مفصّلًا وواضحًا. لا تختصر. لا تحذف خطوة. "
        "أبقِ أسماء الدوال والمكتبات والأوامر بالإنجليزية، والشرح بالعربية."
    ),
}

# --- سيرفر وهمي لإرضاء Render ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass # إخفاء سجلات السيرفر الوهمي

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    log.info(f"Dummy web server running on port {port}")
    server.serve_forever()
# ---------------------------------

def chunk_text(text: str, size: int = 3900) -> list[str]:
    if len(text) <= size:
        return [text] if text else [""]
    chunks = []
    buf = []
    cur = 0
    for line in text.splitlines(keepends=True):
        if cur + len(line) > size and buf:
            chunks.append("".join(buf))
            buf, cur = [], 0
        buf.append(line)
        cur += len(line)
    if buf:
        chunks.append("".join(buf))
    return chunks

async def guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return
    if user.id != OWNER_ID:
        log.warning("blocked user id=%s username=%s", user.id, user.username)
        if update.effective_message:
            await update.effective_message.reply_text("هذا البوت خاص.")
        raise ApplicationHandlerStop

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        await update.message.reply_text(f"معرّفك: `{user.id}`", parse_mode="Markdown")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚙️ توليد كود", callback_data=MODE_GEN)],
            [InlineKeyboardButton("📖 شرح كود", callback_data=MODE_EXPLAIN)],
        ]
    )
    await update.message.reply_text(
        "اختر الوضع:\n"
        "• ⚙️ توليد كود — أرسل وصفًا، يرجّع كود كامل.\n"
        "• 📖 شرح كود — أرسل الكود، يشرح وظيفته وكيف تشغّله بالتفصيل.",
        reply_markup=kb,
    )

async def on_generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data[MODE_KEY] = MODE_GEN
    await q.edit_message_text("⚙️ أرسل وصف الكود المطلوب.")
    return WAITING_PROMPT

async def on_explain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data[MODE_KEY] = MODE_EXPLAIN
    await q.edit_message_text("📖 أرسل الكود وسأشرح وظيفته ومتطلباته وخطوات تشغيله.")
    return WAITING_PROMPT

async def on_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt = (update.message.text or "").strip()
    if not prompt:
        await update.message.reply_text("الرسالة فارغة.")
        return WAITING_PROMPT

    mode = context.user_data.get(MODE_KEY, MODE_GEN)
    status = await update.message.reply_text("⏳ جاري المعالجة...")

    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPTS[mode]},
                {"role": "user", "content": prompt},
            ],
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
    except Exception as exc:
        log.exception("llm call failed")
        await status.edit_text(f"❌ فشل الاتصال: {exc}")
        return WAITING_PROMPT

    if not content.strip():
        await status.edit_text("❌ رد فارغ. جرّب وصفًا أوضح.")
        return WAITING_PROMPT

    await status.delete()
    for chunk in chunk_text(content):
        await update.message.reply_text(chunk)

    await update.message.reply_text("✅ تم. /start للبدء من جديد.")
    context.user_data.pop(MODE_KEY, None)
    return ConversationHandler.END

async def on_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(MODE_KEY, None)
    await update.message.reply_text("تم الإلغاء.")
    return ConversationHandler.END

def main() -> None:
    # تشغيل السيرفر الوهمي في الخلفية عشان Render ما يطفي البوت
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(TypeHandler(Update, guard), group=-1)
    app.add_handler(CommandHandler("id", cmd_id), group=0)

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(on_generate, pattern=f"^{MODE_GEN}$"),
            CallbackQueryHandler(on_explain, pattern=f"^{MODE_EXPLAIN}$"),
        ],
        states={
            WAITING_PROMPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_prompt)
            ],
        },
        fallbacks=[CommandHandler("cancel", on_cancel)],
        per_chat=True,
        per_user=True,
    )

    app.add_handler(CommandHandler("start", cmd_start), group=0)
    app.add_handler(conv, group=0)

    log.info("bot starting — model=%s owner=%s", MODEL, OWNER_ID)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
