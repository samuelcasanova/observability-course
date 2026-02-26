#!/usr/bin/env python3
"""
Traffic simulator for the Food Delivery Tracker.
Sends a continuous stream of orders to the Order Service.

Usage:
    python simulate.py              # default: 1 order every 2 seconds
    python simulate.py --rate 0.5   # 1 order every 0.5 seconds (faster)
    python simulate.py --count 20   # send exactly 20 orders then exit
"""

import argparse
import random
import time
import urllib.request
import urllib.error
import json
import sys

ORDER_SERVICE_URL = "http://localhost:8000"

RESTAURANTS = ["Bella Napoli", "Sushi Garden", "Burger Palace", "Taco Fiesta", "La Boulangerie"]
MENUS = {
    "Bella Napoli": ["Margherita", "Quattro Stagioni", "Tiramisu", "Panna Cotta"],
    "Sushi Garden": ["Salmon Roll", "Miso Soup", "Tempura", "Edamame"],
    "Burger Palace": ["Double Bacon", "Veggie Burger", "Sweet Potato Fries", "Milkshake"],
    "Taco Fiesta": ["Burrito", "Nachos", "Guacamole", "Churros"],
    "La Boulangerie": ["Croissant", "Pain au Chocolat", "Quiche", "Café au Lait"],
}
CUSTOMERS = ["Alice", "Bob", "Carlos", "Diana", "Eve", "Frank", "Grace", "Hugo"]


def create_order() -> dict:
    restaurant = random.choice(RESTAURANTS)
    items = random.sample(MENUS[restaurant], k=random.randint(1, 3))
    customer = random.choice(CUSTOMERS)
    return {"restaurant": restaurant, "items": items, "customer": customer}


def post_order(payload: dict) -> dict | None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ORDER_SERVICE_URL}/orders",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [HTTP {e.code}] {body[:120]}", flush=True)
        return None
    except Exception as e:
        print(f"  [ERROR] {e}", flush=True)
        return None


def main():
    parser = argparse.ArgumentParser(description="Food Delivery Traffic Simulator")
    parser.add_argument("--rate", type=float, default=2.0, help="Seconds between orders (default: 2)")
    parser.add_argument("--count", type=int, default=0, help="Number of orders to send (0 = infinite)")
    args = parser.parse_args()

    print(f"🚀 Simulator starting — 1 order every {args.rate}s", flush=True)
    if args.count:
        print(f"   Will send {args.count} orders then exit.", flush=True)

    sent = 0
    try:
        while True:
            order = create_order()
            print(f"→ [{sent + 1}] Ordering {order['items']} from {order['restaurant']} for {order['customer']}...", flush=True)
            result = post_order(order)
            if result:
                print(f"  ✓ Order {result.get('id')} — status: {result.get('status')}", flush=True)
            sent += 1
            if args.count and sent >= args.count:
                print(f"\n✅ Done — {sent} orders sent.", flush=True)
                break
            time.sleep(args.rate)
    except KeyboardInterrupt:
        print(f"\n⏹  Simulator stopped — {sent} orders sent.", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
