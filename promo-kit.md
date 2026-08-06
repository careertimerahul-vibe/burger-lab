# The Burger Lab — Promo Kit & Message Drafting Rules

Single source of truth for Burger Lab marketing messages. Business facts (links, phone, hours, address, prices) update HERE first — no duplicate hardcoding elsewhere. If a message references a business fact, it comes from this file or `config.js`.

## Canonical facts

- **Brand:** 100% vegetarian, air-fried, late-evening food cart at Amrapali Golf Homes
- **Menu link (USE THIS in messages):** `https://theburgerlabnoida.netlify.app/` — the native landing page
- **WhatsApp orders phone:** `9205491224` → `wa.me/919205491224` (always 91 prefix; bare 10-digit numbers misroute)
- **WhatsApp group invite:** `https://chat.whatsapp.com/ITnN3ll8cBiIFnEQysWuLu`
- **Address (marketing):** Near Entry Gate No. 3, Beside Vegetable Shop, Amrapali Golf Homes Market, Sector 4, Greater Noida
- **Address (shop unit, config.js):** Shop C-29, Amrapali Golf Homes Market, Haibatpur, Sector 4, Greater Noida, UP 201016
- **Hours:** 5 PM – 1 AM, open daily (config.js / README / whatsapp_messages.py all agree)
- **Food court kitchen id:** 5 (live menu/prices ground truth: `menu_items` WHERE `kitchen_id=5` in the burgerlab DB)

## Drafting checklist — ALWAYS include

1. **Menu link** = native landing page `https://theburgerlabnoida.netlify.app/` — NEVER the food court deep link `aghfoodcourt.netlify.app/#kitchen/5`
2. **WhatsApp group invite** (`https://chat.whatsapp.com/ITnN3ll8cBiIFnEQysWuLu`) as the engagement CTA — NEVER "Rate us on Google"
3. **Ordering path** — WhatsApp order link `wa.me/919205491224`
4. **Business facts** — hours (5 PM – 1 AM), 100% veg + air-fried, address when location matters
5. **Combo/offer prices from the LIVE menu** (query food court DB `menu_items` for kitchen_id=5) — never guess a price or combo

## NEVER

- Non-veg references — brand is strictly vegetarian, zero exceptions
- "Rate us on Google" — group invite is the CTA instead
- Food court deep link `#kitchen/5` — native landing page only
- Fabricated prices, combos, phone numbers, or emails
- Publish/send customer-facing messages without Rahul approval (unless explicitly asked)

## Style

- Short, WhatsApp-punchy, pun-filled, Hinglish casual
- Local hooks: evening cravings, weather (hazy/cloudy/rainy/monsoon), weekend mood, student/office crowd
- Emojis generously — 1 per line minimum, visually scannable
- Keep evergreen unless a dated campaign is requested
- Deliver ready-to-send copy in a **code block** (copy-paste ready)
- Offer variants when asked: WhatsApp (casual, Hinglish) + NBH (professional, English)

## Known combos (verify live before sending)

- **₹130 combo** — "Alu Tikki + Fries + Coke" (Burger Combo): OG Alu Tikki Burger · French Fries · Coke (menu_item id 365, category 🔥 Combos)
- Full combo list also has ₹180 / ₹220 / ₹240 / ₹270 options — verify against `menu_items` for kitchen_id=5

## Where the facts live

- `config.js` — business info + full menu (the ONLY file to edit for site business data)
- `README.md` — setup checklist, address, group link, Google Business profile items
- `scripts/whatsapp_messages.py` — context feed generator (weather, wa_link, hours)
- `AGENTS.md` — brand hard rules
- Food court DB `menu_items` for kitchen_id=5 — live price ground truth
