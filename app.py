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

DATA_FILE = os.environ.get(
    "DATA_FILE",
    "results.json"
)

results = []

lock = threading.Lock()


# =========================
# FAYLNI SAQLASH
# =========================

def load_results():

    global results

    try:

        if os.path.exists(DATA_FILE):

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(data, list):

                results = [
                    float(x)
                    for x in data
                    if float(x) >= 1.00
                ]

        print(
            f"Tarix yuklandi: {len(results)} ta natija"
        )

    except Exception as e:

        print(
            "Tarixni yuklash xatosi:",
            e
        )

        results = []


def save_results():

    try:

        temp_file = DATA_FILE + ".tmp"

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                results,
                f,
                ensure_ascii=False
            )

        os.replace(
            temp_file,
            DATA_FILE
        )

        print(
            f"Tarix saqlandi: {len(results)} ta"
        )

    except Exception as e:

        print(
            "Saqlash xatosi:",
            e
        )


# =========================
# TELEGRAM
# =========================

def telegram(method, data=None):

    url = f"{API}/{method}"

    if data is None:
        data = {}

    encoded = urllib.parse.urlencode(
        data
    ).encode()

    try:

        req = urllib.request.Request(
            url,
            data=encoded,
            method="POST"
        )

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode()
            )

    except Exception as e:

        print(
            "Telegram API xatosi:",
            e
        )

        return None


def send_message(chat_id, text):

    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
    )


# =========================
# STATISTIKA
# =========================

def get_distribution(data):

    groups = {
        "1.00-1.49": 0,
        "1.50-1.99": 0,
        "2.00-2.99": 0,
        "3.00-4.99": 0,
        "5.00+": 0
    }

    if not data:
        return groups

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

        percent = (
            count / total * 100
        )

        lines.append(
            f"{name}x: "
            f"{percent:.1f}% "
            f"({count} ta)"
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

        return (
            "📊 Hozircha hech qanday "
            "natija yo‘q."
        )

    average = (
        sum(data) / total
    )

    last10 = data[-10:]
    last20 = data[-20:]
    last50 = data[-50:]

    text = (
        "📊 <b>AVIATOR STATISTIK TAHLIL</b>\n\n"
    )

    text += (
        f"Jami raundlar: "
        f"<b>{total}</b>\n"
    )

    text += (
        f"O‘rtacha koeffitsiyent: "
        f"<b>{average:.2f}x</b>\n\n"
    )

    text += (
        "📈 <b>Barcha tarix:</b>\n"
    )

    text += distribution_text(
        data
    )

    if last10:

        avg10 = (
            sum(last10) /
            len(last10)
        )

        text += (
            "\n\n🔹 <b>Oxirgi 10 raund:</b>\n"
        )

        text += (
            f"O‘rtacha: "
            f"<b>{avg10:.2f}x</b>\n"
        )

        text += distribution_text(
            last10
        )

    if last20:

        avg20 = (
            sum(last20) /
            len(last20)
        )

        text += (
            "\n\n🔹 <b>Oxirgi 20 raund:</b>\n"
        )

        text += (
            f"O‘rtacha: "
            f"<b>{avg20:.2f}x</b>\n"
        )

        text += distribution_text(
            last20
        )

    if last50:

        avg50 = (
            sum(last50) /
            len(last50)
        )

        text += (
            "\n\n🔹 <b>Oxirgi 50 raund:</b>\n"
        )

        text += (
            f"O‘rtacha: "
            f"<b>{avg50:.2f}x</b>\n"
        )

        text += distribution_text(
            last50
        )

    text += (
        "\n\n⚠️ Bu faqat tarixiy statistika. "
        "Keyingi raund natijasini "
        "kafolatlamaydi."
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
            f"📊 Hozir tarixda: "
            f"<b>{total} ta</b>\n"
            "Kamida 10 ta natija kerak."
        )

    # Oxirgi 100 ta yoki mavjud barcha natija

    sample = data

    sample_sorted = sorted(
        sample
    )

    n = len(sample_sorted)

    # Statistik chegaralar

    low_index = int(
        (n - 1) * 0.20
    )

    high_index = int(
        (n - 1) * 0.80
    )

    low = sample_sorted[
        low_index
    ]

    high = sample_sorted[
        high_index
    ]

    low = round(
        low,
        1
    )

    high = round(
        high,
        1
    )

    # Eng ko‘p uchragan diapazon

    groups = get_distribution(
        sample
    )

    best = max(
        groups,
        key=groups.get
    )

    best_count = groups[
        best
    ]

    best_percent = (
        best_count / n * 100
    )

    avg = (
        sum(sample) / n
    )

    text = (
        "🔮 <b>KEYINGI RAUND UCHUN "
        "STATISTIK TAHLIL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"📊 Tahlil qilingan tarix: "
        f"<b>{n} ta</b>\n"

        f"📈 O‘rtacha koeffitsiyent: "
        f"<b>{avg:.2f}x</b>\n\n"

        "🎯 <b>Statistik diapazon:</b>\n"
        f"<b>{low:.1f}x — {high:.1f}x</b>\n\n"

        f"⬇️ <b>Eng past chegara: "
        f"{low:.1f}x</b>\n"

        f"⬆️ <b>Yuqori chegara: "
        f"{high:.1f}x</b>\n\n"

        "📌 <b>Eng ko‘p uchragan "
        "diapazon:</b>\n"

        f"<b>{best}</b> — "
        f"<b>{best_percent:.1f}%</b>\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        f"🎯 <b>Statistik signal: "
        f"{low:.1f}x dan boshlanadi</b>\n\n"

        "⚠️ Bu kafolatli bashorat emas."
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

                value = float(
                    number.replace(
                        ",",
                        "."
                    )
                )

                if value >= 1.00:

                    results.append(
                        value
                    )

                    added += 1

            except ValueError:

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
        "👋 <b>Aviator Stat Bot "
        "ishlayapti!</b>\n\n"

        "📥 <b>Natija qo‘shish:</b>\n"
        "/add 1.24 2.10 1.05 3.50\n\n"

        "📊 <b>Statistikani ko‘rish:</b>\n"
        "/stat\n\n"

        "🔮 <b>Keyingi round uchun "
        "statistik tahlil:</b>\n"
        "/predict\n\n"

        "🗑 <b>Tarixni tozalash:</b>\n"
        "/clear\n\n"

        "📚 Bot yuborilgan natijalarni "
        "tarixga qo‘shib boradi."
    )


# =========================
# COMMAND
# =========================

def process_message(message):

    if "text" not in message:
        return

    chat_id = message[
        "chat"
    ]["id"]

    text = message[
        "text"
    ].strip()


    # =====================
    # START
    # =====================

    if text.startswith(
        "/start"
    ):

        send_message(
            chat_id,
            help_text()
        )


    # =====================
    # HELP
    # =====================

    elif text.startswith(
        "/help"
    ):

        send_message(
            chat_id,
            help_text()
        )


    # =====================
    # ADD
    # =====================

    elif text.startswith(
        "/add"
    ):

        parts = text.split()[1:]

        if not parts:

            send_message(
                chat_id,
                "❗ Masalan:\n"
                "/add 1.24 2.10 "
                "1.05 3.50"
            )

            return

        added = add_results(
            parts
        )

        with lock:

            total = len(results)


        # Qo‘shilgan natijalar haqida xabar

        send_message(
            chat_id,
            f"✅ <b>{added}</b> ta "
            f"natija qo‘shildi.\n"
            f"📚 Jami tarix: "
            f"<b>{total}</b> ta"
        )


        # =====================
        # MUHIM:
        # ADD DAN KEYIN
        # AVTOMATIK SIGNAL
        # =====================

        send_message(
            chat_id,
            make_predict()
        )


    # =====================
    # STAT
    # =====================

    elif text.startswith(
        "/stat"
    ):

        send_message(
            chat_id,
            make_stat()
        )


    # =====================
    # PREDICT
    # =====================

    elif text.startswith(
        "/predict"
    ):

        send_message(
            chat_id,
            make_predict()
        )


    # =====================
    # CLEAR
    # =====================

    elif text.startswith(
        "/clear"
    ):

        clear_results()

        send_message(
            chat_id,
            "🗑 <b>Barcha tarix "
            "tozalandi.</b>\n"
            "📚 Jami natija: <b>0 ta</b>"
        )


    # =====================
    # NOT FOUND
    # =====================

    else:

        send_message(
            chat_id,
            "❓ Buyruqni tushunmadim.\n\n"
            "/start — yordam\n"
            "/add — natija qo‘shish\n"
            "/stat — statistika\n"
            "/predict — statistik tahlil\n"
            "/clear — tarixni tozalash"
        )


# =========================
# BOT LOOP
# =========================

def bot_loop():

    offset = None

    print(
        "🤖 Bot ishga tushdi!"
    )

    while True:

        try:

            data = {
                "timeout": 25
            }

            if offset is not None:

                data[
                    "offset"
                ] = offset

            response = telegram(
                "getUpdates",
                data
            )

            if (
                response
                and response.get("ok")
            ):

                updates = response.get(
                    "result",
                    []
                )

                for update in updates:

                    offset = (
                        update[
                            "update_id"
                        ] + 1
                    )

                    if "message" in update:

                        process_message(
                            update[
                                "message"
                            ]
                        )

        except Exception as e:

            print(
                "Bot loop xatosi:",
                e
            )

            time.sleep(3)


# =========================
# RAILWAY WEB SERVER
# =========================

class Handler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        body = (
            b"Aviator Stat Bot OK"
        )

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "text/plain; "
            "charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def log_message(
        self,
        format,
        *args
    ):

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
    os.environ.get(
        "PORT",
        8080
    )
)


server = HTTPServer(
    ("0.0.0.0", port),
    Handler
)


print(
    f"Bot ishga tushdi: {port}"
)


server.serve_forever()
