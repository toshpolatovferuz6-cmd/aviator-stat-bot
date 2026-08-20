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

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        values = [1.24, 2.10, 1.05, 3.50, 1.80, 2.40, 5.20]

        result = analyze(values)

        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()

        self.wfile.write(
            ("AVIATOR STATISTIK TAHLIL\n\n" + result).encode("utf-8")
        )

    def log_message(self, format, *args):
        pass

port = int(os.environ.get("PORT", 8080))

server = HTTPServer(("0.0.0.0", port), Handler)
print(f"Server ishga tushdi: {port}")
server.serve_forever()
