#!/usr/bin/env python3
"""
Burger Lab - Context Feed for WhatsApp Message Generator
Outputs current context (weather, time, day, menu) as JSON for the LLM cron agent.
The agent uses this data to write creative, fun, pun-filled WhatsApp messages.
"""

import subprocess
import json
import os
import re
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
_README_PATH = os.path.join(_PROJECT_DIR, "README.md")


def _load_address():
    try:
        with open(_README_PATH, "r") as f:
            content = f.read()
        match = re.search(r"\*\*(The Burger Lab.+?)\*\*", content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return "The Burger Lab, Near Entry Gate No. 3, Besides Vegetable Shop, Amrapali Golf Homes Market, Sector 4, Greater Noida"


def get_time_of_day():
    hour = datetime.now(IST).hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def get_weather():
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

                if "rain" in condition or "drizzle" in condition or "shower" in condition:
                    return {"type": "rain", "desc": condition, "temp": temp}
                elif "snow" in condition or "frost" in condition or temp < 15:
                    return {"type": "cold", "desc": condition, "temp": temp}
                elif temp > 35 or "sunny" in condition or "clear" in condition:
                    return {"type": "hot", "desc": condition, "temp": temp}
                else:
                    return {"type": "normal", "desc": condition, "temp": temp}
    except Exception:
        pass
    return {"type": "normal", "desc": "clear", "temp": 30}


def main():
    now = datetime.now(IST)
    weather = get_weather()

    context = {
        "day": now.strftime("%A"),
        "date": now.strftime("%d %B"),
        "time_ist": now.strftime("%I:%M %p"),
        "time_of_day": get_time_of_day(),
        "is_weekend": now.weekday() >= 5,
        "weather": weather,
        "address": _load_address(),
        "whatsapp": "9205491224",
        "wa_link": "wa.me/919205491224",
        "whatsapp_group": "https://chat.whatsapp.com/ITnN3ll8cBiIFnEQysWuLu",
        "business_hours": "5 PM - 12 AM",
        "menu": {
            "bestsellers": [
                {"name": "Tandoori Paneer Burger", "price": 140},
                {"name": "Paneer Paradise Burger", "price": 100},
                {"name": "Fully Loaded Fries", "price": 130},
                {"name": "Double Beast Burger", "price": 120},
                {"name": "Paneer Garden Royale", "price": 130},
            ],
            "air_fried": [
                {"name": "Air Fried Paneer Burger", "price": 110, "tag": "healthier option"},
                {"name": "Air Fried Veggie Burger", "price": 90, "tag": "healthier option"},
                {"name": "Air Fried Peri Peri Fries", "price": 80, "tag": "healthier option"},
                {"name": "Air Fried Cheesy Bites", "price": 70, "tag": "healthier option"},
            ],
            "combos": [
                {"name": "Jalapeno Inferno + Peri Peri Fries", "price": 180},
                {"name": "Paneer Paradise + Jalapeno Inferno + Fries", "price": 220},
                {"name": "Paneer Garden Royale + Loaded Fries", "price": 240},
                {"name": "Tandoori Paneer + Loaded Fries + Coke", "price": 270},
            ],
            "sides": [
                {"name": "Peri Peri Fries (Large)", "price": 110},
                {"name": "Cheesy Fries", "price": 100},
                {"name": "Choco Lava Cake", "price": 70},
            ],
        },
        "air_fried_available": True,
        "air_fried_note": "We serve Air Fried options — same great taste, less oil. Perfect for health-conscious foodies.",
    }

    print(json.dumps(context, indent=2))


if __name__ == "__main__":
    main()
