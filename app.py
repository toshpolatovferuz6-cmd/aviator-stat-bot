import os
import json
import time
import math
import random
import threading
import urllib.request
import urllib.parse
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer


# =========================================================
# SOZLAMALAR
# =========================================================

TOKEN = (
    os.environ.get("TELEGRAM_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
    or os.environ.get("TOKEN")
)

if not TOKEN:
    raise RuntimeError("Telegram token topilmadi!")

API = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = os.environ.get("DATA_FILE", "results.json")

results = []
lock = threading.Lock()


# =========================================================
# FAYL SAQLASH / YUKLASH
# =========================================================

def load_results():
    global results

    try:
        if os.path.exists(DATA_FILE):

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):

                cleaned = []

                for x in data:
                    try:
                        value = float(x)

                        if value >= 1.0:
                            cleaned.append(value)

                    except Exception:
                        pass

                results = cleaned

        print(f"Tarix yuklandi: {len(results)} ta")

    except Exception as e:

        print("Tarixni yuklash xatosi:", e)
        results = []


def save_results():

    try:

        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                results,
                f,
                ensure_ascii=False
            )

        os.replace(temp_file, DATA_FILE)

        print(f"Tarix saqlandi: {len(results)} ta")

    except Exception as e:

        print("Saqlash xatosi:", e)


# =========================================================
# TELEGRAM API
# =========================================================

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

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode()
            )

    except Exception as e:

        print("Telegram API xatosi:", e)
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


# =========================================================
# DIAPAZONLAR
# =========================================================

RANGES = [
    ("1.00-1.19", 1.00, 1.20),
    ("1.20-1.49", 1.20, 1.50),
    ("1.50-1.99", 1.50, 2.00),
    ("2.00-2.49", 2.00, 2.50),
    ("2.50-2.99", 2.50, 3.00),
    ("3.00-3.99", 3.00, 4.00),
    ("4.00-4.99", 4.00, 5.00),
    ("5.00-9.99", 5.00, 10.00),
    ("10.00-19.99", 10.00, 20.00),
    ("20.00-49.99", 20.00, 50.00),
    ("50.00-99.99", 50.00, 100.00),
    ("100.00+", 100.00, float("inf")),
]


def get_range_name(value):

    for name, low, high in RANGES:

        if low <= value < high:
            return name

    return "100.00+"


def get_distribution(data):

    counter = Counter()

    for value in data:
        counter[get_range_name(value)] += 1

    return counter


def distribution_text(data):

    if not data:
        return "Ma'lumot yo‘q."

    counter = get_distribution(data)

    total = len(data)

    lines = []

    for name, low, high in RANGES:

        count = counter.get(name, 0)

        percent = count / total * 100

        lines.append(
            f"• {name}x — {percent:.2f}% ({count} ta)"
        )

    return "\n".join(lines)


# =========================================================
# PERCENTILE
# =========================================================

def percentile(data, p):

    if not data:
        return 0.0

    values = sorted(data)

    if len(values) == 1:
        return values[0]

    index = (len(values) - 1) * p

    lower = int(math.floor(index))
    upper = int(math.ceil(index))

    if lower == upper:
        return values[lower]

    weight = index - lower

    return (
        values[lower] * (1 - weight)
        + values[upper] * weight
    )


# =========================================================
# ENTROPY
# =========================================================

def entropy(data):

    if not data:
        return 0.0

    counter = get_distribution(data)

    total = len(data)

    result = 0.0

    for count in counter.values():

        if count <= 0:
            continue

        p = count / total

        result -= p * math.log2(p)

    return result


# =========================================================
# AUTOCORRELATION
# =========================================================

def autocorrelation(data, lag=1):

    n = len(data)

    if n <= lag + 1:
        return 0.0

    x = data

    mean = sum(x) / n

    numerator = 0.0
    denominator = 0.0

    for i in range(lag, n):

        numerator += (
            (x[i] - mean)
            * (x[i - lag] - mean)
        )

    for value in x:

        denominator += (
            (value - mean) ** 2
        )

    if denominator == 0:
        return 0.0

    return numerator / denominator


# =========================================================
# STREAK
# =========================================================

def current_low_streak(data, threshold=1.50):

    count = 0

    for value in reversed(data):

        if value < threshold:
            count += 1
        else:
            break

    return count


def current_high_streak(data, threshold=5.00):

    count = 0

    for value in reversed(data):

        if value >= threshold:
            count += 1
        else:
            break

    return count


# =========================================================
# OXSHASH KETMA-KETLIKLAR
# =========================================================

def transition_analysis(data):

    if len(data) < 2:
        return None

    transitions = {}

    for i in range(len(data) - 1):

        a = get_range_name(data[i])
        b = get_range_name(data[i + 1])

        if a not in transitions:
            transitions[a] = Counter()

        transitions[a][b] += 1

    current = get_range_name(data[-1])

    if current not in transitions:
        return None

    counter = transitions[current]

    total = sum(counter.values())

    if total == 0:
        return None

    best_range, best_count = counter.most_common(1)[0]

    percent = best_count / total * 100

    return (
        current,
        best_range,
        percent,
        total
    )


# =========================================================
# CHI-SQUAREGA O‘XSHASH TEST
# =========================================================

def distribution_uniformity(data):

    if len(data) < 10:
        return 0.0

    counter = get_distribution(data)

    categories = len(RANGES)

    expected = len(data) / categories

    if expected == 0:
        return 0.0

    chi = 0.0

    for name, _, _ in RANGES:

        observed = counter.get(name, 0)

        chi += (
            (observed - expected) ** 2
            / expected
        )

    return chi


# =========================================================
# TREND
# =========================================================

def trend_slope(data):

    n = len(data)

    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2
    y_mean = sum(data) / n

    numerator = 0.0
    denominator = 0.0

    for i, value in enumerate(data):

        numerator += (
            (i - x_mean)
            * (value - y_mean)
        )

        denominator += (
            (i - x_mean) ** 2
        )

    if denominator == 0:
        return 0.0

    return numerator / denominator


# =========================================================
# ASOSIY STATISTIKA
# =========================================================

def calculate_stats(data):

    n = len(data)

    if n == 0:
        return None

    average = sum(data) / n

    minimum = min(data)
    maximum = max(data)

    median = percentile(data, 0.50)

    q1 = percentile(data, 0.25)
    q3 = percentile(data, 0.75)

    p10 = percentile(data, 0.10)
    p90 = percentile(data, 0.90)

    variance = sum(
        (x - average) ** 2
        for x in data
    ) / n

    std = math.sqrt(variance)

    cv = 0.0

    if average != 0:
        cv = std / average * 100

    return {
        "n": n,
        "average": average,
        "minimum": minimum,
        "maximum": maximum,
        "median": median,
        "q1": q1,
        "q3": q3,
        "p10": p10,
        "p90": p90,
        "std": std,
        "cv": cv
    }


# =========================================================
# ROLLING TAHLIL
# =========================================================

def rolling_analysis(data):

    windows = [
        10,
        25,
        50,
        100,
        250,
        500,
        1000
    ]

    lines = []

    for window in windows:

        if len(data) < window:
            continue

        part = data[-window:]

        avg = sum(part) / len(part)

        med = percentile(part, 0.50)

        low = sum(
            1
            for x in part
            if x < 1.50
        )

        low_percent = (
            low / len(part) * 100
        )

        lines.append(
            f"• {window} raund: "
            f"avg {avg:.2f}x | "
            f"median {med:.2f}x | "
            f"<1.50x {low_percent:.1f}%"
        )

    if not lines:
        return "Yetarli ma'lumot yo‘q."

    return "\n".join(lines)


# =========================================================
# BOOTSTRAP ISHONCH ORALIG‘I
# =========================================================

def bootstrap_mean(data, iterations=200):

    n = len(data)

    if n < 20:
        return None

    rng = random.Random(42)

    means = []

    # Juda katta tarixda hisoblashni yengil qilish
    sample_size = min(n, 1000)

    for _ in range(iterations):

        total = 0.0

        for _ in range(sample_size):

            total += data[
                rng.randrange(n)
            ]

        means.append(
            total / sample_size
        )

    means.sort()

    low = means[
        int(len(means) * 0.025)
    ]

    high = means[
        int(len(means) * 0.975)
    ]

    return low, high


# =========================================================
# CHUQUR PREDICT
# =========================================================

def make_predict():

    with lock:
        data = list(results)

    total = len(data)

    if total < 10:

        return (
            "🔮 <b>CHUQUR STATISTIK TAHLIL</b>\n\n"
            f"📊 Hozir tarixda: <b>{total} ta</b>\n\n"
            "Kamida <b>10 ta</b> natija kerak."
        )

    stats = calculate_stats(data)

    average = stats["average"]
    median = stats["median"]

    q1 = stats["q1"]
    q3 = stats["q3"]

    p10 = stats["p10"]
    p90 = stats["p90"]

    std = stats["std"]
    cv = stats["cv"]

    # -----------------------------------------------------
    # ENG KO‘P UCHRAYDIGAN DIAPAZON
    # -----------------------------------------------------

    distribution = get_distribution(data)

    best_range, best_count = (
        distribution.most_common(1)[0]
    )

    best_percent = (
        best_count / total * 100
    )

    # -----------------------------------------------------
    # STREAK
    # -----------------------------------------------------

    low_streak = current_low_streak(
        data,
        1.50
    )

    high_streak = current_high_streak(
        data,
        5.00
    )

    # -----------------------------------------------------
    # AUTOCORRELATION
    # -----------------------------------------------------

    ac1 = autocorrelation(
        data,
        1
    )

    ac2 = autocorrelation(
        data,
        2
    )

    ac3 = autocorrelation(
        data,
        3
    )

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    slope = trend_slope(data)

    # -----------------------------------------------------
    # ENTROPY
    # -----------------------------------------------------

    ent = entropy(data)

    # -----------------------------------------------------
    # CHI-SQUARE
    # -----------------------------------------------------

    chi = distribution_uniformity(
        data
    )

    # -----------------------------------------------------
    # OXSHASH KETMA-KETLIK
    # -----------------------------------------------------

    transition = transition_analysis(
        data
    )

    # -----------------------------------------------------
    # BOOTSTRAP
    # -----------------------------------------------------

    bootstrap = bootstrap_mean(data)

    # -----------------------------------------------------
    # ROLLING
    # -----------------------------------------------------

    rolling = rolling_analysis(
        data
    )

    # -----------------------------------------------------
    # ISHONCH DARAJASI
    # -----------------------------------------------------

    score = 50.0

    # Namuna kattaligi
    if total >= 100:
        score += 10

    if total >= 500:
        score += 10

    if total >= 1000:
        score += 10

    # Kuchli autokorrelyatsiya bo'lsa
    if abs(ac1) > 0.10:
        score += 5

    if abs(ac2) > 0.10:
        score += 3

    # Juda katta o'zgaruvchanlik
    if cv > 100:
        score -= 10

    score = max(
        0,
        min(100, score)
    )

    if score >= 75:
        confidence = "YUQORI"
    elif score >= 55:
        confidence = "O‘RTA"
    else:
        confidence = "PAST"

    # -----------------------------------------------------
    # SIGNAL
    # -----------------------------------------------------

    signal_low = q1
    signal_high = q3

    # Juda ekstremal qiymatlarni signalga kiritmaslik
    signal_low = max(
        1.00,
        round(signal_low, 2)
    )

    signal_high = max(
        signal_low,
        round(signal_high, 2)
    )

    # -----------------------------------------------------
    # MATN
    # -----------------------------------------------------

    text = (
        "🔮 <b>CHUQUR STATISTIK TAHLIL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"📚 <b>To‘liq tarix:</b> {total:,} ta\n"
        f"📈 <b>O‘rtacha:</b> {average:.2f}x\n"
        f"📌 <b>Median:</b> {median:.2f}x\n"
        f"📉 <b>Q1:</b> {q1:.2f}x\n"
        f"📈 <b>Q3:</b> {q3:.2f}x\n"
        f"📊 <b>P10:</b> {p10:.2f}x\n"
        f"📊 <b>P90:</b> {p90:.2f}x\n"
        f"📐 <b>Standart og‘ish:</b> {std:.2f}\n"
        f"📊 <b>O‘zgaruvchanlik:</b> {cv:.1f}%\n\n"

        "🎯 <b>ASOSIY STATISTIK DIAPAZON</b>\n"
        f"<b>{signal_low:.2f}x — {signal_high:.2f}x</b>\n\n"

        f"📍 Eng ko‘p uchragan diapazon:\n"
        f"<b>{best_range}x</b> — "
        f"<b>{best_percent:.2f}%</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔁 <b>KETMA-KETLIK TAHLILI</b>\n\n"

        f"🔻 Hozirgi <1.50x streak: "
        f"<b>{low_streak}</b>\n"

        f"🔺 Hozirgi ≥5.00x streak: "
        f"<b>{high_streak}</b>\n\n"

        f"🔗 Autokorrelyatsiya L1: "
        f"<b>{ac1:.4f}</b>\n"

        f"🔗 Autokorrelyatsiya L2: "
        f"<b>{ac2:.4f}</b>\n"

        f"🔗 Autokorrelyatsiya L3: "
        f"<b>{ac3:.4f}</b>\n\n"

        f"🧮 Entropiya: <b>{ent:.3f}</b>\n"
        f"🧪 Chi-square ko‘rsatkichi: "
        f"<b>{chi:.2f}</b>\n"

        f"📈 Trend slope: <b>{slope:.5f}</b>\n\n"
    )

    # -----------------------------------------------------
    # TRANSITION
    # -----------------------------------------------------

    if transition:

        current, next_range, percent, count = (
            transition
        )

        text += (
            "🔄 <b>OLDINGI DIAPAZONDAN KEYINGI NATIJALAR</b>\n\n"
            f"Hozirgi diapazon: <b>{current}x</b>\n"
            f"Eng ko‘p kuzatilgan keyingi diapazon: "
            f"<b>{next_range}x</b>\n"
            f"Tarixiy ulushi: <b>{percent:.2f}%</b>\n"
            f"Namuna: <b>{count} ta</b>\n\n"
        )

    # -----------------------------------------------------
    # BOOTSTRAP
    # -----------------------------------------------------

    if bootstrap:

        b_low, b_high = bootstrap

        text += (
            "🧪 <b>BOOTSTRAP TAHLILI</b>\n\n"
            f"O‘rtacha uchun taxminiy 95% interval:\n"
            f"<b>{b_low:.2f}x — {b_high:.2f}x</b>\n\n"
        )

    # -----------------------------------------------------
    # ROLLING
    # -----------------------------------------------------

    text += (
        "📊 <b>ROLLING TAHLIL</b>\n\n"
        f"{rolling}\n\n"
    )

    # -----------------------------------------------------
    # ISHONCH
    # -----------------------------------------------------

    text += (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>STATISTIK SIGNAL:</b>\n"
        f"<b>{signal_low:.2f}x — {signal_high:.2f}x</b>\n\n"

        f"🧠 <b>Statistik ishonchlilik:</b> "
        f"<b>{confidence}</b>\n"
        f"📊 Hisoblangan ball: <b>{score:.0f}/100</b>\n\n"

        "⚠️ <b>MUHIM:</b>\n"
        "Bu tarixiy statistik tahlil. "
        "Agar raundlar mustaqil tasodifiy RNG orqali "
        "yaratilsa, tarix keyingi raundni kafolatli "
        "bashorat qila olmaydi."
    )

    return text


# =========================================================
# ODDIY STATISTIKA
# =========================================================

def make_stat():

    with lock:
        data = list(results)

    total = len(data)

    if total == 0:

        return (
            "📊 Hozircha hech qanday natija yo‘q."
        )

    stats = calculate_stats(data)

    text = (
        "📊 <b>AVIATOR STATISTIKASI</b>\n\n"
        f"Jami raundlar: <b>{total:,}</b>\n"
        f"O‘rtacha: <b>{stats['average']:.2f}x</b>\n"
        f"Median: <b>{stats['median']:.2f}x</b>\n"
        f"Minimum: <b>{stats['minimum']:.2f}x</b>\n"
        f"Maksimum: <b>{stats['maximum']:.2f}x</b>\n\n"

        "📊 <b>Barcha tarix:</b>\n"
        f"{distribution_text(data)}\n\n"
    )

    windows = [
        10,
        20,
        50,
        100,
        500,
        1000
    ]

    for window in windows:

        if total >= window:

            part = data[-window:]

            avg = sum(part) / len(part)

            text += (
                f"\n🔹 Oxirgi {window} raund: "
                f"<b>{avg:.2f}x</b>\n"
                f"{distribution_text(part)}\n"
            )

    text += (
        "\n⚠️ Bu tarixiy statistika. "
        "Keyingi natijani kafolatlamaydi."
    )

    return text


# =========================================================
# ADD
# =========================================================

def add_results(numbers):

    added = 0

    with lock:

        for number in numbers:

            try:

                value = float(number)

                if value >= 1.00:

                    results.append(value)

                    added += 1

            except Exception:
                pass

        if added > 0:
            save_results()

    return added


# =========================================================
# CLEAR
# =========================================================

def clear_results():

    global results

    with lock:

        results = []

        save_results()

    return True


# =========================================================
# HELP
# =========================================================

def hel
