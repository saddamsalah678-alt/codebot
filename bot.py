# bot.py — Telegram bot: تنفيذ مباشر + بحث في الدارك ويب مع ترجمة تلقائية
import os
import logging
import threading
import asyncio
import requests
import re
from bs4 import BeautifulSoup
import urllib.parse
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("codebot")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

client = AsyncOpenAI(
    api_key="not-needed",
    base_url=os.environ.get("OPENAI_BASE_URL", "https://text.pollinations.ai/openai"),
)
MODEL = os.environ.get("MODEL", "openai")
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "4096"))

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args): pass

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    log.info(f"Dummy web server running on port {port}")
    server.serve_forever()

def chunk_text(text: str, size: int = 3900) -> list[str]:
    if len(text) <= size: return [text] if text else [""]
    chunks, buf, cur = [], [], 0
    for line in text.splitlines(keepends=True):
        if cur + len(line) > size and buf:
            chunks.append("".join(buf)); buf, cur = [], 0
        buf.append(line); cur += len(line)
    if buf: chunks.append("".join(buf))
    return chunks

def is_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF]', text))

async def translate_to_english(text: str) -> str:
    if not is_arabic(text): return text
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Translate the following search query to English for a dark web search engine. Output only the translated text, no extra words."},
                {"role": "user", "content": text}
            ],
            max_tokens=50, temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except:
        return text

def darkweb_search(query: str) -> str:
    try:
        log.info(f"Searching darkweb for: {query}")
        q = urllib.parse.quote(query)
        search_url = f"https://ahmia.fi/search/?q={q}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for a in soup.find_all('a', href=True):
            link = a['href']
            title = a.text.strip()
            
            if '.onion' in link and "juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd" not in link:
                if not link.startswith('http'): 
                    link = "http://" + link
                if len(title) > 3:
                    results.append(f"- {title}\n  {link}")
                
        if not results:
            return "❌ لم يتم العثور على نتائج. جرب البحث بالإنجليزية للحصول على نتائج أدق."
        
        unique_results = list(dict.fromkeys(results))
        return "📌 **النتائج من الدارك ويب:**\n\n" + "\n\n".join(unique_results[:10])
    except Exception as e:
        return f"❌ فشل البحث: {str(e)}"

def fetch_darkweb_text(url: str) -> str:
    try:
        clean_url = url.replace("http://", "").replace("https://", "")
        if clean_url.endswith(".onion"):
            gateway_url = f"https://{clean_url}.ws"
        else:
            gateway_url = url
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(gateway_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator='\n')[:4000]
    except Exception as e:
        return f"❌ فشل الجلب (تأكد من الرابط): {str(e)}"

def download_darkweb_file(url: str) -> str:
    try:
        clean_url = url.replace("http://", "").replace("https://", "")
        if clean_url.endswith(".onion"):
            gateway_url = f"https://{clean_url}.ws"
        else:
            gateway_url = url

        local_filename = os.path.join(tempfile.gettempdir(), clean_url.split('/')[-1] or "file_dump")
        with requests.get(gateway_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename
    except Exception as e:
        log.error(f"Download failed: {e}")
        return ""

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text(
        "أنا تحت أمرك يا سيدي.\n"
        "أرسل طلبك مباشرة (مثل: ابحث عن كتاب cybersecurity) وسأتصرف.\n"
        "أو استخدم الأوامر المباشرة:\n"
        "`!explain <رابط>`\n`!book <اسم>`\n`!data <اسم>`\n`!search <كلمة>`\n`!download <رابط>`", 
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID: return
    prompt = (update.message.text or "").strip()
    if not prompt: return

    prompt_lower = prompt.lower()
    darkweb_keywords = ["مسربة", "تسريب", "بيانات", "دارك", "dark", "leak", "dump", "combolist"]
    book_keywords = ["كتاب", "كتب", "book", "pdf", "امن", "أمن", "سيبراني"]

    if any(k in prompt_lower for k in darkweb_keywords) or any(k in prompt_lower for k in book_keywords):
        status = await update.message.reply_text("🕵️‍♂️ جاري تجهيز البحث في الدارك ويب...")
        
        # تنظيف الكلمات العربية
        query = prompt.replace("ابحث عن", "").replace("مسربة", "").replace("بيانات", "").replace("اريد", "").replace("كتاب", "").replace("من الدرك ويب", "").strip()
        
        # ترجمة تلقائية إذا كان النص عربي
        if is_arabic(query):
            await status.edit_text("🔄 جاري ترجمة الطلب للبحث في الدارك ويب...")
            query = await translate_to_english(query)
            await status.edit_text(f"🕵️‍♂️ جاري البحث عن: {query}")

        result = darkweb_search(query)
        await status.delete()
        for chunk in chunk_text(result): await update.message.reply_text(chunk)
        return

    if prompt.startswith("!book "):
        status = await update.message.reply_text("📚 جاري البحث عن كتب...")
        q = prompt.replace("!book ", "")
        if is_arabic(q): q = await translate_to_english(q)
        result = darkweb_search(q)
        await status.delete()
        for chunk in chunk_text(result): await update.message.reply_text(chunk)
        return

    if prompt.startswith("!data "):
        status = await update.message.reply_text("🗄️ جاري البحث عن بيانات...")
        q = prompt.replace("!data ", "")
        if is_arabic(q): q = await translate_to_english(q)
        result = darkweb_search(q)
        await status.delete()
        for chunk in chunk_text(result): await update.message.reply_text(chunk)
        return

    if prompt.startswith("!search "):
        status = await update.message.reply_text("🔍 جاري البحث...")
        q = prompt.replace("!search ", "")
        if is_arabic(q): q = await translate_to_english(q)
        result = darkweb_search(q)
        await status.delete()
        for chunk in chunk_text(result): await update.message.reply_text(chunk)
        return

    if prompt.startswith("!download "):
        url = prompt.replace("!download ", "")
        status = await update.message.reply_text("📥 جاري التحميل...")
        file_path = download_darkweb_file(url)
        await status.delete()
        if file_path and os.path.exists(file_path):
            await update.message.reply_document(document=open(file_path, 'rb'), filename=os.path.basename(file_path))
            os.remove(file_path)
        else:
            await update.message.reply_text("❌ فشل التحميل.")
        return

    if prompt.startswith("!explain "):
        url = prompt.replace("!explain ", "")
        status = await update.message.reply_text("🧠 جاري سحب الكود وشرحه...")
        code_text = fetch_darkweb_text(url)
        
        sys_prompt = "أنت خبير برمجة. اشرح هذا الكود وفائدته."
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": code_text}],
                max_tokens=MAX_OUTPUT_TOKENS, temperature=0.2,
            )
            content = resp.choices[0].message.content or ""
        except Exception as e:
            content = f"❌ فشل الشرح: {e}"
        await status.delete()
        for chunk in chunk_text(content): await update.message.reply_text(chunk)
        return

    status = await update.message.reply_text("⏳ جاري التنفيذ...")
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "أنت خادم مطيع. نفذ طلب السيد فوراً."}, {"role": "user", "content": prompt}],
            max_tokens=MAX_OUTPUT_TOKENS, temperature=0.1,
        )
        content = resp.choices[0].message.content or ""
    except Exception as exc:
        await status.edit_text(f"❌ فشل الاتصال: {exc}")
        return

    await status.delete()
    for chunk in chunk_text(content): await update.message.reply_text(chunk)

def main() -> None:
    asyncio.set_event_loop(asyncio.new_event_loop())
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("bot starting — model=%s owner=%s", MODEL, OWNER_ID)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
