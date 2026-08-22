import os
import json
import time
import threading
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# =========================
# SOZLAMALAR
# =========================

TOKEN = (
    os.environ.get("TELEGRAM_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
    or os.environ.get("TOKEN")
)

if not TOKEN:
    raise RuntimeError("Telegram token topilmadi!")

API = f"https://api.telegram.org/bot{TOKEN}"

# Railway Volume ulansa shu joyga saqlash mumkin.
# Oddiy holatda ham ishlaydi.
DATA_FILE = os.environ.get("DATA_FILE", "results.json")

results = []
lock = threading.Lock()


# =========================
# FAYLNI SAQLASH
# =========================

def load_results():
    global results

    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                results = [float(x) for x in data]

        print(f"Tarix yuklandi: {len(results)} ta natija")

    except Exception as e:
        print("Tarixni yuklash xatosi:", e)
        results = []


def save_results():
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False)

        os.replace(temp_file, DATA_FILE)

        print(f"Tarix saqlandi: {len(results)} ta")

    except Exception as e:
        print("Saqlash xatosi:", e)


# =========================
# TELEGRAM
# =========================

def telegram(method, data=None):

    url = f"{API}/{method}"

    if data is None:
        data = {}

    encoded = urllib.parse.urlencode(data).encode()

    try:
        req = urllib.request.Request(
            url,
            data=encoded,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    except Exception as e:
        print("Telegram API xatosi:", e)
        return None


def send_message(chat_id, text):

    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


# =========================
# STATISTIKA
# =========================

def get_distribution(data):

    if not data:
        return {
            "1.00-1.49": 0,
            "1.50-1.99": 0,
            "2.00-2.99": 0,
            "3.00-4.99": 0,
            "5.00+": 0
        }

    groups = {
        "1.00-1.49": 0,
        "1.50-1.99": 0,
        "2.00-2.99": 0,
        "3.00-4.99": 0,
        "5.00+": 0
    }

    for x in data:

        if x < 1.50:
            groups["1.00-1.49"] += 1

        elif x < 2.00:
            groups["1.50-1.99"] += 1

        elif x < 3.00:
            groups["2.00-2.99"] += 1

        elif x < 5.00:
            groups["3.00-4.99"] += 1

        else:
            groups["5.00+"] += 1

    return groups


def distribution_text(data):

    groups = get_distribution(data)

    total = len(data)

    if total == 0:
        return "Ma'lumot yetarli emas."

    lines = []

    for name, count in groups.items():

        percent = count / total * 100

        lines.append(
            f"{name}x: {percent:.1f}% ({count} ta)"
        )

    return "\n".join(lines)


# =========================
# STAT
# =========================

def make_stat():

    with lock:
        data = list(results)

    total = len(data)

    if total == 0:
        return "📊 Hozircha hech qanday natija yo‘q."

    average = sum(data) / total

    last10 = data[-10:]
    last20 = data[-20:]
    last50 = data[-50:]

    text = "📊 AVIATOR STATISTIK TAHLIL\n\n"

    text += f"Jami raundlar: {total}\n"
    text += f"O‘rtacha koeffitsiyent: {average:.2f}x\n\n"

    text += "📈 Barcha tarix:\n"
    text += distribution_text(data)

    if last10:
        avg10 = sum(last10) / len(last10)

        text += "\n\n🔹 Oxirgi 10 raund:\n"
        text += f"O‘rtacha: {avg10:.2f}x\n"
        text += distribution_text(last10)

    if last20:
        avg20 = sum(last20) / len(last20)

        text += "\n\n🔹 Oxirgi 20 raund:\n"
        text += f"O‘rtacha: {avg20:.2f}x\n"
        text += distribution_text(last20)

    if last50:
        avg50 = sum(last50) / len(last50)

        text += "\n\n🔹 Oxirgi 50 raund:\n"
        text += f"O‘rtacha: {avg50:.2f}x\n"
        text += distribution_text(last50)

    text += (
        "\n\n⚠️ Bu faqat tarixiy statistika. "
        "Keyingi raund natijasini kafolatlamaydi."
    )

    return text


# =========================
# PREDICT
# =========================

def make_predict():
    with lock:
        data = list(results)

    total = len(data)

    if total < 10:
        return (
            "🔮 <b>STATISTIK TAHLIL</b>\n\n"
            f"📊 Hozir tarixda: <b>{total} ta</b>\n"
            "Kamida 10 ta natija kerak."
        )

    # Oxirgi 100 ta yoki mavjud barcha natija
    sample = data[-100:]
    sample_sorted = sorted(sample)

    n = len(sample_sorted)

    # Statistik chegaralar
    low_index = int((n - 1) * 0.20)
    high_index = int((n - 1) * 0.80)

    low = sample_sorted[low_index]
    high = sample_sorted[high_index]

    # Pastki chegarani 0.1x ko'rinishida yaxlitlash
    low = round(low, 1)
    high = round(high, 1)

    # Eng ko'p uchragan diapazon
    groups = get_distribution(sample)

    best = max(groups, key=groups.get)
    best_count = groups[best]
    best_percent = best_count / n * 100

    avg = sum(sample) / n

    text = (
        "🔮 <b>KEYINGI RAUND UCHUN STATISTIK TAHLIL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"📊 Tahlil qilingan tarix: <b>{n} ta</b>\n"
        f"📈 O‘rtacha koeffitsiyent: <b>{avg:.2f}x</b>\n\n"

        "🎯 <b>Eng ehtimoliy diapazon:</b>\n"
        f"<b>{low:.1f}x — {high:.1f}x</b>\n\n"

        f"⬇️ <b>Eng past chegara: {low:.1f}x</b>\n"
        f"⬆️ <b>Yuqori chegara: {high:.1f}x</b>\n\n"

        f"📌 Eng ko‘p uchragan diapazon:\n"
        f"<b>{best}</b> — <b>{best_percent:.1f}%</b>\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Signal: {low:.1f}x dan boshlanadi</b>"
    )

    return text


# =========================
# ADD
# =========================

def add_results(numbers):

    added = 0

    with lock:

        for number in numbers:

            try:
                value = float(number)

                if value >= 1.00:
                    results.append(value)
                    added += 1

            except:
                pass

        if added > 0:
            save_results()

    return added


# =========================
# CLEAR
# =========================

def clear_results():

    global results

    with lock:

        results = []
        save_results()

    return True


# =========================
# HELP
# =========================

def help_text():

    return (
        "👋 Aviator Stat Bot ishlayapti!\n\n"

        "📥 Natija qo‘shish:\n"
        "/add 1.24 2.10 1.05 3.50\n\n"

        "📊 Statistikani ko‘rish:\n"
        "/stat\n\n"

        "🔮 Statistik ehtimolni ko‘rish:\n"
        "/predict\n\n"

        "🗑 Tarixni tozalash:\n"
        "/clear\n\n"

        "📚 Bot yuborgan barcha natijalarni "
        "eski tarixga qo‘shib boradi."
    )


# =========================
# COMMAND
# =========================

def process_message(message):

    if "text" not in message:
        return

    chat_id = message["chat"]["id"]
    text = message["text"].strip()

    if text.startswith("/start"):

        send_message(
            chat_id,
            help_text()
        )

    elif text.startswith("/help"):

        send_message(
            chat_id,
            help_text()
        )

    elif text.startswith("/add"):

        parts = text.split()[1:]

        if not parts:

            send_message(
                chat_id,
                "❗ Masalan:\n/add 1.24 2.10 1.05 3.50"
            )

            return

        added = add_results(parts)

        with lock:
            total = len(results)

        send_message(
            chat_id,
            f"✅ {added} ta natija qo‘shildi.\n\n"
            f"📚 Jami tarix: {total} ta"
        )

    elif text.startswith("/stat"):

        send_message(
            chat_id,
            make_stat()
        )

    elif text.startswith("/predict"):

        send_message(
            chat_id,
            make_predict()
        )

    elif text.startswith("/clear"):

        clear_results()

        send_message(
            chat_id,
            "🗑 Barcha tarix tozalandi.\n"
            "Jami natija: 0 ta"
        )

    else:

        send_message(
            chat_id,
            "❓ Buyruqni tushunmadim.\n\n"
            " /start — yordam\n"
            " /add — natija qo‘shish\n"
            " /stat — statistika\n"
            " /predict — statistik ehtimol\n"
            " /clear — tarixni tozalash"
        )


# =========================
# BOT LOOP
# =========================

def bot_loop():

    offset = None

    print("🤖 Bot ishga tushdi!")

    while True:

        try:

            data = {
                "timeout": 25
            }

            if offset is not None:
                data["offset"] = offset

            response = telegram(
                "getUpdates",
                data
            )

            if response and response.get("ok"):

                updates = response.get("result", [])

                for update in updates:

                    offset = update["update_id"] + 1

                    if "message" in update:
                        process_message(
                            update["message"]
                        )

        except Exception as e:

            print("Bot loop xatosi:", e)
            time.sleep(3)


# =========================
# RAILWAY WEB SERVER
# =========================

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):

        body = b"Aviator Stat Bot OK"

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


# =========================
# START
# =========================

load_results()

threading.Thread(
    target=bot_loop,
    daemon=True
).start()

port = int(
    os.environ.get("PORT", 8080)
)

server = HTTPServer(
    ("0.0.0.0", port),
    Handler
)

print(f"Bot ishga tushdi: {port}")

server.serve_forever()
