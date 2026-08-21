import os
import json
import time
import threading
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = (
    os.environ.get("TELEGRAM_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
    or os.environ.get("TOKEN")
)

if not TOKEN:
    raise RuntimeError("Telegram token topilmadi.")

API = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "results.json"

results = []
offset = 0


def load_results():
    global results
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except:
        results = []


def save_results():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)


def telegram(method, data=None):
    try:
        if data is None:
            data = {}

        encoded = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(
            f"{API}/{method}",
            data=encoded
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    except Exception as e:
        print("Telegram xatosi:", e)
        return None


def send_message(chat_id, text):
    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


def category(x):
    if x < 1.50:
        return "1.00x – 1.49x"
    elif x < 2.00:
        return "1.50x – 1.99x"
    elif x < 3.00:
        return "2.00x – 2.99x"
    elif x < 5.00:
        return "3.00x – 4.99x"
    else:
        return "5.00x+"


def analyze(values):
    if not values:
        return "Ma'lumot kiritilmagan."

    total = len(values)
    average = sum(values) / total

    ranges = {
        "1.00x – 1.49x": 0,
        "1.50x – 1.99x": 0,
        "2.00x – 2.99x": 0,
        "3.00x – 4.99x": 0,
        "5.00x+": 0
    }

    for x in values:
        ranges[category(x)] += 1

    text = "📊 AVIATOR STATISTIK TAHLIL\n\n"
    text += f"Jami raundlar: {total}\n"
    text += f"O'rtacha koeffitsiyent: {average:.2f}x\n\n"

    text += "Tarixiy taqsimot:\n"

    for name, count in ranges.items():
        percent = count / total * 100
        text += f"{name}: {percent:.1f}%\n"

    return text


def predict():
    if len(results) < 10:
        return (
            "🔮 STATISTIK SIGNAL\n\n"
            "Bashorat uchun kamida 10 ta natija kerak.\n"
            f"Hozir: {len(results)} ta natija.\n\n"
            "Ko'proq natija yuboring."
        )

    values = results[-100:]

    ranges = {
        "1.00x – 1.49x": 0,
        "1.50x – 1.99x": 0,
        "2.00x – 2.99x": 0,
        "3.00x – 4.99x": 0,
        "5.00x+": 0
    }

    for x in values:
        ranges[category(x)] += 1

    total = len(values)

    probabilities = {
        name: (count + 1) / (total + len(ranges)) * 100
        for name, count in ranges.items()
    }

    best = max(probabilities, key=probabilities.get)

    text = "🔮 STATISTIK SIGNAL\n\n"
    text += f"Tahlil qilingan raundlar: {total}\n\n"

    text += "Ehtimoliy diapazonlar:\n"

    for name, probability in probabilities.items():
        text += f"{name}: {probability:.1f}%\n"

    text += "\n"
    text += f"📌 Tarix bo'yicha eng yuqori ulush: {best}\n\n"

    recent = results[-10:]
    recent_avg = sum(recent) / len(recent)

    text += f"Oxirgi 10 raund o'rtachasi: {recent_avg:.2f}x\n\n"

    text += (
        "⚠️ Bu faqat statistik hisob-kitob.\n"
        "Keyingi raund natijasini kafolatlamaydi."
    )

    return text


def handle_message(message):
    if "chat" not in message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text.startswith("/start"):
        send_message(
            chat_id,
            "👋 Aviator Stat Bot ishga tushdi!\n\n"
            "📥 Natija qo'shish:\n"
            "/add 1.24 2.10 1.05 3.50\n\n"
            "📊 Statistikani ko'rish:\n"
            "/stat\n\n"
            "🔮 Statistik signal:\n"
            "/predict\n\n"
            "🗑 Natijalarni tozalash:\n"
            "/clear"
        )

    elif text.startswith("/add"):
        try:
            parts = text.split()[1:]

            if not parts:
                send_message(
                    chat_id,
                    "Masalan:\n/add 1.24 2.10 1.05 3.50"
                )
                return

            new_values = []

            for p in parts:
                x = float(p.replace(",", "."))

                if x < 1.00:
                    continue

                new_values.append(x)

            if not new_values:
                send_message(chat_id, "To'g'ri koeffitsiyent kiriting.")
                return

            results.extend(new_values)
            save_results()

            send_message(
                chat_id,
                f"✅ {len(new_values)} ta natija qo'shildi.\n\n"
                + analyze(new_values)
            )

        except Exception:
            send_message(
                chat_id,
                "❌ Format xato.\n\n"
                "Masalan:\n"
                "/add 1.24 2.10 1.05 3.50"
            )

    elif text.startswith("/stat"):
        send_message(chat_id, analyze(results))

    elif text.startswith("/predict"):
        send_message(chat_id, predict())

    elif text.startswith("/clear"):
        results.clear()
        save_results()

        send_message(
            chat_id,
            "🗑 Barcha statistik natijalar tozalandi."
        )


def bot_loop():
    global offset

    telegram("deleteWebhook", {"drop_pending_updates": "true"})

    while True:
        try:
            response = telegram(
                "getUpdates",
                {
                    "timeout": 25,
                    "offset": offset
                }
            )

            if not response or not response.get("ok"):
                time.sleep(3)
                continue

            updates = response.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1

                message = update.get("message")

                if message:
                    handle_message(message)

        except Exception as e:
            print("Bot loop xatosi:", e)
            time.sleep(5)


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        body = (
            "Aviator Stat Bot ishlayapti!\n\n"
            f"Jami saqlangan natijalar: {len(results)}"
        ).encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


load_results()

threading.Thread(
    target=bot_loop,
    daemon=True
).start()

port = int(os.environ.get("PORT", 8080))

server = HTTPServer(
    ("0.0.0.0", port),
    Handler
)

print(f"Bot ishga tushdi: {port}")

server.serve_forever()
