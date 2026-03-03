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
from concurrent.futures import ThreadPoolExecutor

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


def post_order(payload: dict, seq: int) -> None:
    """Send a single order and print the result. Runs in a background thread."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ORDER_SERVICE_URL}/orders",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"  \u2713 [{seq}] Order {result.get('id')} \u2014 status: {result.get('status')}", flush=True)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [HTTP {e.code}] [{seq}] {body[:120]}", flush=True)
    except Exception as e:
        print(f"  [ERROR] [{seq}] {e}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Food Delivery Traffic Simulator")
    parser.add_argument("--rate", type=float, default=2.0, help="Seconds between orders (default: 2)")
    parser.add_argument("--count", type=int, default=0, help="Number of orders to send (0 = infinite)")
    parser.add_argument("--workers", type=int, default=32, help="Max concurrent requests (default: 32)")
    args = parser.parse_args()

    print(f"\U0001f680 Simulator starting \u2014 1 order every {args.rate}s (up to {args.workers} concurrent)", flush=True)
    if args.count:
        print(f"   Will send {args.count} orders then exit.", flush=True)

    sent = 0
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            while True:
                order = create_order()
                sent += 1
                print(
                    f"\u2192 [{sent}] Ordering {order['items']} from {order['restaurant']} for {order['customer']}...",
                    flush=True,
                )
                # Fire-and-forget: the thread handles the HTTP call and response
                # independently, so time.sleep(rate) is the only pacing delay.
                executor.submit(post_order, order, sent)

                if args.count and sent >= args.count:
                    print(f"\n\u23f3 All {sent} orders dispatched \u2014 waiting for responses...", flush=True)
                    break
                time.sleep(args.rate)

    except KeyboardInterrupt:
        print(f"\n\u23f9  Simulator stopped \u2014 {sent} orders dispatched.", flush=True)
        sys.exit(0)

    print(f"\n\u2705 Done \u2014 {sent} orders sent.", flush=True)


if __name__ == "__main__":
    main()
