import os, json, time, threading, urllib.request, urllib.parse
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import math

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
# DIAPAZONLAR
# =========================================================

BINS = [
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


# =========================================================
# SAQLASH
# =========================================================

def load_results():
    global results

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        results = []

        for x in raw:
            try:
                value = float(x)

                if value >= 1.00:
                    results.append(value)

            except Exception:
                pass

        print("Tarix yuklandi:", len(results))

    except Exception:
        results = []

        print("Yangi tarix yaratildi.")


def save_results():

    temp = DATA_FILE + ".tmp"

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False
        )

    os.replace(
        temp,
        DATA_FILE
    )


# =========================================================
# TELEGRAM
# =========================================================

def telegram(method, data=None):

    try:

        body = urllib.parse.urlencode(
            data or {}
        ).encode()

        request = urllib.request.Request(
            f"{API}/{method}",
            data=body,
            method="POST"
        )

        with urllib.request.urlopen(
            request,
            timeout=35
        ) as response:

            return json.loads(
                response.read().decode()
            )

    except Exception as e:

        print(
            "Telegram xatosi:",
            e
        )

        return None


def send_message(
    chat_id,
    text
):

    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
    )


# =========================================================
# DIAPAZON
# =========================================================

def bin_name(value):

    for name, low, high in BINS:

        if low <= value < high:
            return name

    return "100.00+"


def counts(data):

    return Counter(
        bin_name(x)
        for x in data
    )


def distribution(data):

    if not data:
        return {}

    counter = counts(data)

    total = len(data)

    return {
        name:
        counter.get(name, 0)
        / total
        * 100

        for name, _, _ in BINS
    }


# =========================================================
# PERCENTILE
# =========================================================

def percentile(
    data,
    p
):

    if not data:
        return 0.0

    values = sorted(data)

    position = (
        len(values) - 1
    ) * p

    lower = int(
        math.floor(position)
    )

    upper = int(
        math.ceil(position)
    )

    if lower == upper:
        return values[lower]

    weight = position - lower

    return (
        values[lower]
        +
        (
            values[upper]
            -
            values[lower]
        )
        * weight
    )


# =========================================================
# ASOSIY STATISTIKA
# =========================================================

def calculate_stats(data):

    n = len(data)

    if n == 0:
        return None

    average = (
        sum(data) / n
    )

    variance = sum(
        (x - average) ** 2
        for x in data
    ) / n

    return {
        "n": n,
        "average": average,
        "median": percentile(data, 0.50),
        "q1": percentile(data, 0.25),
        "q3": percentile(data, 0.75),
        "p10": percentile(data, 0.10),
        "p90": percentile(data, 0.90),
        "std": math.sqrt(variance),
        "minimum": min(data),
        "maximum": max(data)
    }


# =========================================================
# ENTROPY
# =========================================================

def entropy(data):

    if not data:
        return 0.0

    counter = counts(data)

    total = len(data)

    result = 0.0

    for count in counter.values():

        if count <= 0:
            continue

        p = count / total

        result -= (
            p * math.log2(p)
        )

    return result


# =========================================================
# AUTOCORRELATION
# =========================================================

def autocorrelation(
    data,
    lag
):

    n = len(data)

    if n <= lag + 1:
        return 0.0

    average = sum(data) / n

    denominator = sum(
        (x - average) ** 2
        for x in data
    )

    if denominator == 0:
        return 0.0

    numerator = sum(
        (data[i] - average)
        *
        (data[i - lag] - average)

        for i in range(
            lag,
            n
        )
    )

    return (
        numerator
        /
        denominator
    )


# =========================================================
# STREAK
# =========================================================

def streak(
    data,
    threshold,
    below=True
):

    total = 0

    for value in reversed(data):

        condition = (
            value < threshold
        )

        if condition == below:
            total += 1
        else:
            break

    return total


# =========================================================
# TRANSITION
# =========================================================

def transition_analysis(data):

    if len(data) < 2:
        return None

    transitions = defaultdict(
        Counter
    )

    for a, b in zip(
        data,
        data[1:]
    ):

        transitions[
            bin_name(a)
        ][
            bin_name(b)
        ] += 1

    current = bin_name(
        data[-1]
    )

    counter = transitions[
        current
    ]

    if not counter:
        return None

    name, number = (
        counter.most_common(1)[0]
    )

    total = sum(
        counter.values()
    )

    return (
        current,
        name,
        number / total * 100,
        total
    )


# =========================================================
# O‘XSHASH PATTERN
# =========================================================

def similarity_analysis(
    data,
    length=5
):

    if len(data) < length + 2:
        return None

    target = [
        bin_name(x)
        for x in data[-length:]
    ]

    matches = []

    for i in range(
        length,
        len(data) - 1
    ):

        pattern = [
            bin_name(x)
            for x in data[
                i - length:i
            ]
        ]

        if pattern == target:

            matches.append(
                data[i]
            )

    if not matches:
        return None

    counter = counts(matches)

    name, number = (
        counter.most_common(1)[0]
    )

    percent = (
        number
        /
        len(matches)
        *
        100
    )

    return (
        name,
        percent,
        len(matches)
    )


# =========================================================
# TREND
# =========================================================

def trend_slope(data):

    n = len(data)

    if n < 2:
        return 0.0

    x_mean = (
        n - 1
    ) / 2

    y_mean = (
        sum(data) / n
    )

    denominator = sum(
        (i - x_mean) ** 2
        for i in range(n)
    )

    if denominator == 0:
        return 0.0

    numerator = sum(
        (i - x_mean)
        *
        (value - y_mean)

        for i, value
        in enumerate(data)
    )

    return (
        numerator
        /
        denominator
    )


# =========================================================
# RUNS TEST
# =========================================================

def runs_test(data):

    if len(data) < 20:
        return None

    binary = [
        value < 2.0
        for value in data
    ]

    n1 = sum(binary)
    n2 = len(binary) - n1

    if n1 == 0 or n2 == 0:
        return None

    runs = 1

    for i in range(
        1,
        len(binary)
    ):

        if binary[i] != binary[i - 1]:
            runs += 1

    expected = (
        1
        +
        (
            2
            *
            n1
            *
            n2
            /
            (n1 + n2)
        )
    )

    variance = (
        2
        *
        n1
        *
        n2
        *
        (
            2 * n1 * n2
            -
            n1
            -
            n2
        )
        /
        (
            (n1 + n2) ** 2
            *
            (n1 + n2 - 1)
        )
    )

    if variance <= 0:
        return 0.0

    return (
        runs - expected
    ) / math.sqrt(
        variance
    )


# =========================================================
# ROLLING
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

        average = (
            sum(part)
            /
            len(part)
        )

        median = percentile(
            part,
            0.50
        )

        low = sum(
            1
            for x in part
            if x < 1.50
        )

        low_percent = (
            low
            /
            len(part)
            *
            100
        )

        lines.append(
            f"• {window} raund: "
            f"avg {average:.2f}x | "
            f"median {median:.2f}x | "
            f"<1.50x {low_percent:.1f}%"
        )

    if not lines:
        return "Yetarli ma'lumot yo‘q."

    return "\n".join(
        lines
    )


# =========================================================
# WALK-FORWARD BACKTEST
# =========================================================

def backtest(
    data,
    window=100
):

    if len(data) < (
        window + 20
    ):

        return None

    correct = 0
    total = 0

    for i in range(
        window,
        len(data)
    ):

        history = data[
            i - window:i
        ]

        counter = counts(
            history
        )

        predicted = (
            counter
            .most_common(1)[0][0]
        )

        actual = bin_name(
            data[i]
        )

        if predicted == actual:
            correct += 1

        total += 1

    if total == 0:
        return None

    return (
        correct
        /
        total
        *
        100
    )


# =========================================================
# MODEL VOTES
# =========================================================

def model_votes(data):

    votes = Counter()

    # 1. Umumiy tarix
    overall = distribution(
        data
    )

    for name, percent in (
        overall.items()
    ):

        votes[name] += percent

    # 2. Yaqin tarixga vazn
    windows = [
        (25, 2.5),
        (50, 2.0),
        (100, 1.5),
        (250, 1.0),
        (500, 0.7),
        (1000, 0.5)
    ]

    for window, weight in windows:

        if len(data) < window:
            continue

        recent = data[-window:]

        dist = distribution(
            recent
        )

        for name, percent in (
            dist.items()
        ):

            votes[name] += (
                percent
                *
                weight
            )

    # 3. Transition
    transition = (
        transition_analysis(data)
    )

    if transition:

        _, name, percent, _ = (
            transition
        )

        votes[name] += (
            percent * 2
        )

    # 4. Similarity
    similarity = (
        similarity_analysis(
            data,
            5
        )
    )

    if similarity:

        name, percent, _ = (
            similarity
        )

        votes[name] += (
            percent * 3
        )

    return votes


# =========================================================
# YAKUNIY PREDICT
# =========================================================

def make_predict():

    with lock:
        data = list(results)

    total = len(data)

    if total < 10:

        return (
            "🔮 <b>CHUQUR TAHLIL</b>\n\n"
            f"📊 Hozir: <b>{total}</b> ta\n"
            f"❗ Yana "
            f"<b>{10-total}</b> ta "
            "natija kerak."
        )

    stats = calculate_stats(
        data
    )

    votes = model_votes(
        data
    )

    ranked = (
        votes.most_common()
    )

    best = ranked[0][0]

    second = (
        ranked[1][0]
        if len(ranked) > 1
        else best
    )

    lookup = {
        name: (low, high)
        for name, low, high
        in BINS
    }

    low = lookup[best][0]
    high = lookup[best][1]

    if high == float("inf"):

        high = max(
            stats["p90"],
            low * 2
        )

    if second != best:

        low = min(
            low,
            lookup[second][0]
        )

        second_high = (
            lookup[second][1]
        )

        if second_high != float("inf"):

            high = max(
                high,
                second_high
            )

    # Haddan tashqari katta diapazonni
    # p90 bilan cheklash
    if stats["p90"] > low:

        high = min(
            high,
            stats["p90"] * 1.25
        )

    if high <= low:

        high = (
            low + 0.50
        )

    central = (
        low + high
    ) / 2

    agreement = (
        votes[best]
        /
        max(
            1,
            sum(votes.values())
        )
        *
        100
    )

    # Autocorrelation
    autocorrelations = [
        autocorrelation(
            data,
            lag
        )
        for lag in range(1, 6)
    ]

    max_ac = max(
        abs(x)
        for x in autocorrelations
    )

    # Backtest
    backtest_result = (
        backtest(
            data,
            100
        )
    )

    # Confidence — bu
    # model agreement,
    # real probability emas
    confidence = (
        40
        +
        agreement * 0.70
    )

    if (
        backtest_result
        is not None
        and backtest_result > 50
    ):

        confidence += 10

    if max_ac > 0.15:

        confidence += 5

    if max_ac > 0.30:

        confidence -= 10

    confidence = max(
        5,
        min(
            95,
            confidence
        )
    )

    transition = (
        transition_analysis(
            data
        )
    )

    similarity = (
        similarity_analysis(
            data,
            5
        )
    )

    entropy_value = entropy(
        data
    )

    run_value = runs_test(
        data
    )

    slope = trend_slope(
        data
    )

    low_streak = streak(
        data,
        1.50,
        True
    )

    high_streak = streak(
        data,
        5.00,
        False
    )

    text = (
        "🔮 <b>YAKUNIY CHUQUR "
        "STATISTIK TAHLIL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"📚 Tarix: "
        f"<b>{total:,}</b> ta\n"

        f"📈 O‘rtacha: "
        f"<b>{stats['average']:.2f}x</b>\n"

        f"📌 Median: "
        f"<b>{stats['median']:.2f}x</b>\n"

        f"📊 P10: "
        f"<b>{stats['p10']:.2f}x</b>\n"

        f"📊 P90: "
        f"<b>{stats['p90']:.2f}x</b>\n"

        f"📐 Standart og‘ish: "
        f"<b>{stats['std']:.2f}</b>\n\n"

        "🎯 <b>UMUMIY TAXMINIY "
        "DIAPAZON</b>\n"

        f"<b>{low:.2f}x — "
        f"{high:.2f}x</b>\n\n"

        f"⭐ Markaziy qiymat: "
        f"<b>{central:.2f}x</b>\n\n"

        f"🧠 Model kelishuvi: "
        f"<b>{agreement:.1f}%</b>\n"

        f"🎯 Model ishonchliligi: "
        f"<b>{confidence:.0f}/100</b>\n"
    )

    if backtest_result is not None:

        text += (
            f"📈 Walk-forward backtest: "
            f"<b>{backtest_result:.1f}%</b>\n"
        )

    text += (
        "\n🔬 <b>CHUQUR DIAGNOSTIKA</b>\n"

        f"🔗 Max AC(L1-L5): "
        f"<b>{max_ac:.4f}</b>\n"

        f"🧮 Entropiya: "
        f"<b>{entropy_value:.3f}</b>\n"

        f"📈 Trend: "
        f"<b>{slope:.5f}</b>\n"

        f"🔻 <1.50x streak: "
        f"<b>{low_streak}</b>\n"

        f"🔺 5x+ streak: "
        f"<b>{high_streak}</b>\n"
    )

    if run_value is not None:

        text += (
            f"🧪 Runs-test Z: "
            f"<b>{run_value:.3f}</b>\n"
        )

    if transition:

        current, next_range, percent, count = (
            transition
        )

        text += (
            "\n🔄 <b>TRANSITION</b>\n"
            f"{current}x → "
            f"<b>{next_range}x</b>\n"
            f"Tarixiy ulush: "
            f"<b>{percent:.1f}%</b>\n"
            f"Namuna: <b>{count}</b> ta\n"
        )

    if similarity:

        name, percent, count = (
            similarity
        )

        text += (
            "\n🔎 <b>O‘XSHASH PATTERN</b>\n"
            f"Topilgan: <b>{count}</b> ta\n"
            f"Eng ko‘p keyingi diapazon: "
            f"<b>{name}x</b>\n"
            f"Ulushi: <b>{percent:.1f}%</b>\n"
        )

    text += (
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>YAKUNIY SIGNAL:</b>\n"
        f"<b>{low:.2f}x — "
        f"{high:.2f}x</b>\n\n"

        "⚠️ Bu tarixiy statistik model.\n"
        "Agar o‘yin mustaqil kriptografik "
        "RNG ishlatsa, oldingi tarixdan "
        "keyingi raundni aniq bilib "
        "bo‘lmaydi."
    )

    return text


# =========================================================
# STAT
# =========================================================

def make_stat():

    with lock:
        data = list(results)

    if not data:

        return (
            "📊 Hozircha natijalar yo‘q."
        )

    stats = calculate_stats(
        data
    )

    counter = counts(
        data
    )

    text = (
        "📊 <b>AVIATOR STATISTIKASI</b>\n\n"

        f"📚 Jami: "
        f"<b>{len(data):,}</b> ta\n"

        f"📈 O‘rtacha: "
        f"<b>{stats['average']:.2f}x</b>\n"

        f"📌 Median: "
        f"<b>{stats['median']:.2f}x</b>\n"

        f"⬇️ Minimum: "
        f"<b>{stats['minimum']:.2f}x</b>\n"

        f"⬆️ Maksimum: "
        f"<b>{stats['maximum']:.2f}x</b>\n\n"

        "📊 <b>DIAPAZONLAR</b>\n"
    )

    for name, _, _ in BINS:

        count = counter.get(
            name,
            0
        )

        percent = (
            count
            /
            len(data)
            *
            100
        )

        text += (
            f"{name}x: "
            f"<b>{percent:.1f}%</b> "
            f"({count} ta)\n"
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

                value = float(
                    number.replace(
                        ",",
                        "."
                    )
                )

   
