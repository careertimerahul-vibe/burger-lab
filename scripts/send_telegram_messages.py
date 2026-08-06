#!/usr/bin/env python3
"""Send 3 Burger Lab WhatsApp messages to Rahul on Telegram."""
import urllib.request, json, re, sys

# Read token from .env
with open("/opt/data/.env") as f:
    content = f.read()
token_match = re.search(r"TELEGRAM_BOT_TOKEN=(\S+)", content)
token = token_match.group(1)
chat_id = "427257056"

MSG1_HEADER = "*Message 1 - The Pun Master*"
MSG1 = """THE BURGER LAB - Sunday Special

Lettuce be honest... this is the *paneer-ultimate* deal of the weekend

Our *Tandoori Paneer Burger* (140 INR) is so good, even the clouds are jealous

Smoky tandoori paneer
Gooey melted cheese
That signature sauce tho...

It's a *bun-believable* Sunday - come grab yours before we sell out!

Near Entry Gate No. 3, Amrapali Golf Homes Market, Sector 4, Greater Noida
Open 5 PM - 12 AM

Order now: wa.me/919205491224
Join the group for exclusive offers:
https://chat.whatsapp.com/ITnN3ll8iBiIFnEQysWuLu"""

MSG2_HEADER = "*Message 2 - The Storyteller*"
MSG2 = """THE BURGER LAB - Sunday Night Story

It's 10 PM on a Sunday. The haze outside is real. You're scrolling through your phone, stomach growling, and suddenly you remember...

*Fully Loaded Fries exist.* 130 INR. Cheese, jalapenos, and that secret sauce drizzled on top. Life-changing? Absolutely.

But wait - why stop there? Grab the *Paneer Paradise + Jalapeno Inferno + Fries* combo at just 220 INR. That's a whole meal, sorted.

Don't let Sunday night be boring. Let us handle dinner.

Near Entry Gate No. 3, Amrapali Golf Homes Market, Sector 4, Greater Noida
Open till 12 AM - we got you!

Order now: wa.me/919205491224
Join the group:
https://chat.whatsapp.com/ITnN3ll8iBiIFnEQysWuLu"""

MSG3_HEADER = "*Message 3 - The Hype Beast*"
MSG3 = """BRO. SUNDAY = BURGER DAY.

*Double Beast Burger* - 120 INR
Two patties. Double cheese. Zero regrets.

Bestseller. Every. Single. Week.
That cheese pull tho...
Your friends will be jealous

SUNDAY SPECIAL: Order any combo, get a *free Choco Lava Cake* (70 INR value)
Today only. Don't sleep on this.

Near Entry Gate No. 3, Amrapali Golf Homes Market, Sector 4, Greater Noida
5 PM - 12 AM

Hit us up NOW:
wa.me/919205491224

Join the fam:
https://chat.whatsapp.com/ITnN3ll8iBiIFnEQysWuLu"""

messages = [
    (MSG1_HEADER, MSG1),
    (MSG2_HEADER, MSG2),
    (MSG3_HEADER, MSG3),
]

for header, msg in messages:
    full_msg = f"{header}\n\n{msg}"
    data = json.dumps({
        "chat_id": chat_id,
        "text": full_msg,
        "parse_mode": "Markdown"
    }).encode("utf-8")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        if result.get("ok"):
            print(f"SENT: {header}")
        else:
            print(f"FAIL: {header} - {result}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {header} - {e}", file=sys.stderr)
        sys.exit(1)

print("All 3 messages sent successfully!")
