#!/usr/bin/env python3
"""
Burger Lab - WhatsApp Message Generator
Generates 3 ready-to-copy WhatsApp marketing messages based on:
- Current time of day
- Weather in Greater Noida
- Weekend offers
- Mood/vibe variations
"""

import subprocess
import json
import os
import re
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Load address from README (single source of truth) ──────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
_README_PATH = os.path.join(_PROJECT_DIR, "README.md")

def _load_address():
    """Read the address line from README.md so it's always in sync."""
    try:
        with open(_README_PATH, "r") as f:
            content = f.read()
        # Match the line: **The Burger Lab, ...**
        match = re.search(r"\*\*(The Burger Lab.+?)\*\*", content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    # Fallback
    return "The Burger Lab, Near Entry Gate No. 3, Besides Vegetable Shop, Amrapali Golf Homes Market, Sector 4, Greater Noida"

ADDRESS = _load_address()
WHATSAPP = "9205491224"
WA_LINK = "wa.me/919205491224"

# Menu data for reference
MENU_HIGHLIGHTS = {
    "bestsellers": [
        ("Tandoori Paneer Burger", 140),
        ("Paneer Paradise Burger", 100),
        ("Fully Loaded Fries", 130),
        ("Double Beast Burger", 120),
        ("Paneer Garden Royale", 130),
    ],
    "combos": [
        ("Jalapeno Inferno + Peri Peri Fries", 180),
        ("Paneer Paradise + Jalapeno Inferno + Fries", 220),
        ("Paneer Garden Royale + Loaded Fries", 240),
        ("Tandoori Paneer + Loaded Fries + Coke", 270),
    ],
    "sides": [
        ("Peri Peri Fries (L)", 110),
        ("Cheesy Fries", 100),
        ("Choco Lava Cake", 70),
    ]
}

WEEKEND_OFFERS = [
    "🎉 Weekend Special: Get a FREE Choco Lava Cake with any 2 burgers!",
    "🔥 Saturday Deal: Tandoori Paneer + Loaded Fries + Coke @ just 270 (save 40!)",
    "💥 Sunday Combo: Double Beast + Peri Peri Fries + Choco Lava @ just 250!",
    "🌟 Weekend Bonanza: Order any 3 items, get the cheapest one FREE!",
]

TIME_BASED = {
    "morning": {
        "emoji": ["☀️", "🌅", "🍳"],
        "hooks": [
            "Start your day with a burger craving!",
            "Morning munchies? We've got you covered.",
            "Who says burgers are only for dinner? 😏",
        ],
        "vibe": "fresh and energetic"
    },
    "afternoon": {
        "emoji": ["🔥", "🍔", "⚡"],
        "hooks": [
            "Lunch hour = Burger hour!",
            "Beat the heat with our spicy range!",
            "Afternoon cravings hitting different today?",
        ],
        "vibe": "bold and hungry"
    },
    "evening": {
        "emoji": ["🌆", "😋", "🍟"],
        "hooks": [
            "Evening vibes + Burger Lab = Perfect combo!",
            "The sun's setting but our grills are just heating up!",
            "Dinner plans? We've got the best burgers in town!",
        ],
        "vibe": "warm and inviting"
    },
    "night": {
        "emoji": ["🌙", "🌃", "🍔"],
        "hooks": [
            "Late night cravings? We're open till 1 AM!",
            "Midnight munchies? The Burger Lab has you covered!",
            "Can't sleep? Come grab a burger! We're open late!",
        ],
        "vibe": "fun and chill"
    }
}

WEATHER_BASED = {
    "hot": {
        "emoji": ["🥤", "❄️", "🧊"],
        "hooks": [
            "Beat the heat with our creamy range! Ice-cold drinks available 🧊",
            "Too hot to cook? Grab a fresh burger instead!",
            "Stay cool with our Creamy Crispy + cold drink combo!",
        ]
    },
    "rain": {
        "emoji": ["🌧️", "☔", "🍟"],
        "hooks": [
            "Rainy day = Comfort food day! Loaded Fries + Hot Chocolate 🌧️",
            "Monsoon cravings? Our Tandoori Paneer hits different in the rain!",
            "Stuck indoors? WhatsApp your order and enjoy cozy burgers at home!",
        ]
    },
    "cold": {
        "emoji": ["🧣", "🔥", "☕"],
        "hooks": [
            "Chilly evening? Warm up with our sizzling Tandoori Paneer! 🔥",
            "Cold weather calls for hot, cheesy burgers!",
            "Winter special: Hot Choco Lava Cake + any burger = Pure bliss!",
        ]
    },
    "normal": {
        "emoji": ["😋", "🍔", "🎉"],
        "hooks": [
            "Perfect weather for a perfect burger!",
            "Great day to treat yourself! 🍔",
            "The Burger Lab is calling your name!",
        ]
    }
}


def get_time_of_day():
    """Get current time of day category in IST."""
    now = datetime.now(IST)
    hour = now.hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def get_weather():
    """Fetch current weather for Greater Noida."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://wttr.in/Greater+Noida?format=%C+%t+%h+%w&lang=en"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                condition = parts[0].lower()
                temp_str = parts[1].replace("+", "").replace("C", "")
                try:
                    temp = int(temp_str)
                except ValueError:
                    temp = 30

                # Categorize weather
                if "rain" in condition or "drizzle" in condition or "shower" in condition:
                    return "rain", condition, temp
                elif "snow" in condition or "frost" in condition or temp < 15:
                    return "cold", condition, temp
                elif temp > 35 or "sunny" in condition or "clear" in condition:
                    return "hot", condition, temp
                else:
                    return "normal", condition, temp
    except Exception:
        pass
    return "normal", "clear", 30


def is_weekend():
    """Check if today is weekend (Saturday=5, Sunday=6)."""
    return datetime.now(IST).weekday() >= 5


def pick(items):
    """Pick a random item from a list."""
    import random
    return random.choice(items)


def generate_messages():
    """Generate 3 WhatsApp marketing messages."""
    import random

    time_of_day = get_time_of_day()
    weather_type, weather_desc, temp = get_weather()
    weekend = is_weekend()
    now = datetime.now(IST)

    time_data = TIME_BASED[time_of_day]
    weather_data = WEATHER_BASED[weather_type]

    bestseller = pick(MENU_HIGHLIGHTS["bestsellers"])
    combo = pick(MENU_HIGHLIGHTS["combos"])
    side = pick(MENU_HIGHLIGHTS["sides"])

    date_str = now.strftime("%A, %d %B")
    time_str = now.strftime("%I:%M %p")

    messages = []

    # Message 1: Hook + Bestseller + CTA
    msg1 = f"""{pick(time_data["emoji"])} {pick(time_data["hooks"])}

🍔 *{bestseller[0]}* — Just ₹{bestseller[1]}
{pick(weather_data["emoji"])} {pick(weather_data["hooks"])}

{ADDRESS}
WhatsApp: {WHATSAPP}
 Open daily 5PM - 1AM

 Reply with your order, we'll have it ready!{f"""

 *WEEKEND OFFER*: {pick(WEEKEND_OFFERS)}""" if weekend else ""}"""

    messages.append(("Hook + Bestseller", msg1))

    # Message 2: Combo deal focus
    msg2 = f"""{pick(time_data["emoji"])} *DEAL ALERT!* 🔥

💰 *{combo[0]}*
   ➡️ Only ₹{combo[1]}!

🍟 Add {side[0]} for just ₹{side[1]}

{f"🎉 *Weekend Bonus*: {pick(WEEKEND_OFFERS)}" if weekend else f"⏰ {time_str} — {weather_desc}, {temp}°C in Greater Noida"}

 Shop C-29, Amrapali Golf Homes Market, Near Entry Gate No. 3, Besides Vegetable Shop
 Order now: wa.me/919205491224

_The Burger Lab — Gourmet Veg Burgers & Loaded Fries_"""

    messages.append(("Combo Deal", msg2))

    # Message 3: Fun/engagement style
    emoji_burger = pick(["🍔", "🌮", "🍟", "🤤", "🔥"])
    msg3 = f"""{emoji_burger} *{date_str} | {time_str}*

{pick(time_data["hooks"])}

Our Top 3 Bestsellers:
1️⃣ Tandoori Paneer — ₹140
2️⃣ Paneer Paradise — ₹100
3️⃣ Fully Loaded Fries — ₹130

{pick(weather_data["emoji"])} {pick(weather_data["hooks"])}

{f"🎊 *THIS WEEKEND*: {pick(WEEKEND_OFFERS)}" if weekend else ""}

 Tap to order  wa.me/919205491224
 The Burger Lab, Near Entry Gate No. 3, Besides Vegetable Shop, Amrapali Golf Homes, Sector 4, Greater Noida

_Rate us on Google!_ """

    messages.append(("Top 3 Bestsellers", msg3))

    return messages, {
        "time_of_day": time_of_day,
        "weather": f"{weather_desc}, {temp}°C",
        "weekend": weekend,
        "date": date_str,
        "time": time_str,
    }


def main():
    messages, context = generate_messages()

    print(f"# Burger Lab — WhatsApp Messages")
    print(f"**Generated:** {context['date']} at {context['time']} IST")
    print(f"**Weather:** {context['weather']}")
    print(f"**Time of day:** {context['time_of_day']}")
    print(f"**Weekend:** {'Yes' if context['weekend'] else 'No'}")
    print(f"\n---\n")

    for i, (label, msg) in enumerate(messages, 1):
        print(f"## Message {i}: {label}\n")
        print("```")
        print(msg)
        print("```")
        print(f"\n---\n")


if __name__ == "__main__":
    main()
