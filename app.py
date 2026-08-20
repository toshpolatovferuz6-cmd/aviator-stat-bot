from collections import Counter

def analyze(values):
    if not values:
        return "Ma'lumot kiritilmagan."

    total = len(values)

    ranges = {
        "1.00x - 1.49x": 0,
        "1.50x - 1.99x": 0,
        "2.00x - 2.99x": 0,
        "3.00x - 4.99x": 0,
        "5.00x+": 0
    }

    for x in values:
        if x < 1.50:
            ranges["1.00x - 1.49x"] += 1
        elif x < 2.00:
            ranges["1.50x - 1.99x"] += 1
        elif x < 3.00:
            ranges["2.00x - 2.99x"] += 1
        elif x < 5.00:
            ranges["3.00x - 4.99x"] += 1
        else:
            ranges["5.00x+"] += 1

    average = sum(values) / total

    result = []
    result.append(f"Jami raundlar: {total}")
    result.append(f"O'rtacha koeffitsiyent: {average:.2f}x")
    result.append("")
    result.append("Tarixiy statistik taqsimot:")

    for name, count in ranges.items():
        percent = count / total * 100
        result.append(f"{name}: {percent:.1f}%")

    return "\n".join(result)


if __name__ == "__main__":
    print("AVIATOR STATISTIK TAHLIL")
    print("Koeffitsiyentlarni vergul bilan kiriting.")
    print("Masalan: 1.24, 2.10, 1.05, 3.50, 5.20")
    print()

    text = input("Natijalar: ")

    try:
        values = [
            float(x.strip().replace("x", ""))
            for x in text.split(",")
            if x.strip()
        ]

        print()
        print(analyze(values))

    except ValueError:
        print("Xato: faqat raqamli koeffitsiyent kiriting.")
