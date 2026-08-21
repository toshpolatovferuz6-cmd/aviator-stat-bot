import os
import json
import threading
import time
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = (
    os.environ.get("TELEGRAM_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
    or os.environ.get("TOKEN")
)

if not TOKEN:
    raise RuntimeError("Telegram token topilmadi")

API = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "results.json"

results = []


def load_results():
    global results
    try:
        with open(DATA_FILE, "r") as f:
            results = json.load(f)
    except:
        results = []


def save_results():
    with open(DATA_FILE, "w") as f:
        json.dump(results[-500:], f)


def telegram(method, data=None):
    url = f"{API}/{method}"

    if data:
        encoded = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(url, data=encoded)
    else:
        request = urllib.request.Request(url)

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def send_message(chat_id, text):
    telegram("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


def analyze():
    if not results:
        return "📊 Hali natijalar kiritilmagan."

    total = len(results)
    average = sum(results) / total

    groups = {
        "1.00x – 1.49x": 0,
        "1.50x – 1.99x": 0,
        "2.00x – 2.99x": 0,
        "3.00x – 4.99x": 0,
        "5.00x+": 0
    }

    for x in results:
        if x < 1.50:
            groups["1.00x – 1.49x"] += 1
        elif x < 2.00:
            groups["1.50x – 1.99x"] += 1
        elif x < 3.00:
            groups["2.00x – 2.99x"] += 1
        elif x < 5.00:
            groups["3.00x – 4.99x"] += 1
        else:
            groups["5.00x+"] += 1

    text = "📊 AVIATOR STATISTIK TAHLIL\n\n"
    text += f"Jami raundlar: {total}\n"
    text += f"O‘rtacha koeffitsiyent: {average:.2f}x\n\n"
    text += "Tarixiy taqsimot:\n"

    for name, count in groups.items():
        percent = count / total * 100
        text += f"{name}: {percent:.1f}%\n"

    text += "\n⚠️ Bu statistik ma’lumot. Keyingi raund natijasini kafolatlamaydi."

    return text


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text == "/start":
        send_message(
            chat_id,
            "👋 Aviator Stat Bot ishga tushdi!\n\n"
            "📥 Natija qo‘shish:\n"
            "/add 1.24 2.10 1.05 3.50\n\n"
            "📊 Statistikani ko‘rish:\n"
            "/stat\n\n"
            "🗑 Natijalarni tozalash:\n"
            "/clear"
        )
        return

    if text.startswith("/add"):
        parts = text.split()[1:]

        if not parts:
            send_message(
                chat_id,
                "Masalan:\n/add 1.24 2.10 1.05 3.50"
            )
            return

        added = 0

        for item in parts:
            try:
                value = float(item.replace("x", "").replace("X", ""))
                if value >= 1:
                    results.append(value)
                    added += 1
            except:
                pass

        save_results()

        send_message(
            chat_id,
            f"✅ {added} ta natija qo‘shildi.\n\n" + analyze()
        )
        return

    if text == "/stat":
        send_message(chat_id, analyze())
        return

    if text == "/clear":
        results.clear()
        save_results()
        send_message(chat_id, "🗑 Barcha natijalar tozalandi.")
        return

    if text:
        try:
            value = float(text.replace("x", "").replace("X", ""))

            if value >= 1:
                results.append(value)
                save_results()

                send_message(
                    chat_id,
                    f"✅ {value:.2f}x qo‘shildi.\n\n" + analyze()
                )
                return
        except:
            pass


def bot_loop():
    offset = 0

    while True:
        try:
            response = telegram("getUpdates", {
                "timeout": 25,
                "offset": offset
            })

            for update in response.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update:
                    handle_message(update["message"])

        except Exception as e:
            print("Bot xatosi:", e)
            time.sleep(5)


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"Aviator Stat Bot ishlayapti!"
        )

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
