# The Burger Lab — Promo Kit & Message Drafting Rules

Single source of truth for Burger Lab marketing messages. Business facts (links, phone, hours, address, prices) update HERE first — no duplicate hardcoding elsewhere. If a message references a business fact, it comes from this file or `config.js`.

## Canonical facts

- **Brand:** 100% vegetarian, air-fried, late-evening food cart at Amrapali Golf Homes
- **Menu link (USE THIS in messages):** `https://theburgerlabnoida.netlify.app/` — the native landing page
- **WhatsApp orders phone:** `9205491224` (always 91 prefix; bare 10-digit numbers misroute). Not linked in posts any more — the site takes the order, and posts carry one `Menu & Order` link only.
- **Fulfilment: pickup only — no delivery.** Every post ends with `🥡 Pickup only — no delivery`, appended by the scheduler (`PICKUP_LINE` in `scripts/group_scheduler.py`); never write or vary it in copy, and never promise a rider.
- **WhatsApp group invite:** `https://chat.whatsapp.com/ITnN3ll8cBiIFnEQysWuLu`
- **Address (marketing):** Near Entry Gate No. 3, Beside Vegetable Shop, Amrapali Golf Homes Market, Sector 4, Greater Noida
- **Address (shop unit, config.js):** Shop C-29, Amrapali Golf Homes Market, Haibatpur, Sector 4, Greater Noida, UP 201016
- **Hours:** 5 PM – 12 AM, open daily
- **Food court kitchen id:** 5 (live menu/prices ground truth: `menu_items` WHERE `kitchen_id=5` in the burgerlab DB)

## Drafting checklist — ALWAYS include

0. **Crowd photos get a crowd line.** Whenever the attached photo shows people, a queue or the cart itself, the caption must carry a line about them — "the crowd doesn't lie", "same scene every evening: burger fans, no empty chairs", "look at the line, that's the review". Never describe the crowd in a way the photo contradicts.

1. **Menu link** = native landing page `https://theburgerlabnoida.netlify.app/` — NEVER the food court deep link `aghfoodcourt.netlify.app/#kitchen/5`
2. **WhatsApp group invite** (`https://chat.whatsapp.com/ITnN3ll8cBiIFnEQysWuLu`) as the engagement CTA — NEVER "Rate us on Google". **Exception:** two groups ban external invite links (FOODIES OF GHKW, AGHKW ADVERTISING GROUP) — there the invite is omitted and the menu link carries the CTA. Every other group gets the invite. Machine-enforced via `allow_group_link` in `data/groups.json` (default for a new group: allowed).
3. **Ordering path** — WhatsApp order link `wa.me/919205491224`
4. **Business facts** — hours (5 PM – 12 AM), 100% veg + air-fried, address when location matters
5. **Combo/offer prices from the LIVE menu** (query food court DB `menu_items` for kitchen_id=5) — never guess a price or combo

## NEVER

- Non-veg references — brand is strictly vegetarian, zero exceptions
- **Grilled Pineapple — never promoted in any message** (Rahul, 13 Nov 2026). Machine-enforced: `data/menu_blocklist.json` + a fail-closed check in `scripts/group_scheduler.py`. Add future exclusions to that JSON, not here.
- "Rate us on Google" — group invite is the CTA instead
- Food court deep link `#kitchen/5` — native landing page only
- Fabricated prices, combos, phone numbers, or emails
- Publish/send customer-facing messages without Rahul approval (unless explicitly asked)

## Style

- **English only — always.** Hinglish and typed-Hindi hooks (kit 101–150) stay dormant until Rahul
  explicitly asks for them for a specific slot or group; no auto-mixing. Every queue message carries
  `lang: en` until he says otherwise.
- Short, WhatsApp-punchy, pun-filled
- Local hooks: evening cravings, weather (hazy/cloudy/rainy/monsoon), weekend mood, student/office crowd
- Emojis generously — 1 per line minimum, visually scannable
- Keep evergreen unless a dated campaign is requested
- Deliver ready-to-send copy in a **code block** (copy-paste ready)

## Known combos (verify live before sending)

- **₹130 combo** — "Alu Tikki + Fries + Coke" (Burger Combo): OG Alu Tikki Burger · French Fries · Coke (menu_item id 365, category 🔥 Combos)
- Full combo list also has ₹180 / ₹220 / ₹240 / ₹270 options — verify against `menu_items` for kitchen_id=5

## Copy source — copywriter kit (added 14 Nov 2026)

`copywriter-kit.md` holds the 100 approved hooks and the 3-part message stack. Use it for the
WORDS; this file stays the source of FACTS. Where the two disagree, these win:

- **Facts**: links, phone, address, hours and price floors come from here / `config.js`. The kit's
  rupee figures, percentages and promo codes are examples — ignore any that the live menu
  (`menu_items`, kitchen_id=5) does not confirm.
- **Invite link**: the kit says "always include both links" — overridden by `data/groups.json`
  `allow_group_link`. FOODIES OF GHKW and AGHKW-Advertising are `false`, so those posts carry no
  `chat.whatsapp.com` line at all; the menu link is the CTA.
- **Item-agnostic captions**: hooks that name an item (aloo tikki, paneer, "Double Beast") cannot
  ride a photo, and every current slot has one. Adapt them to generic sensory words —
  `scripts/group_scheduler.py` blocks item names on photo posts.
- **Length/emoji for group posts**: kit's 50–85 words, 2–4 emojis replaces "1 emoji per line".
- **Language**: English only (hooks 1–100). Hinglish/typed-Hindi hooks (101–150) are DORMANT — do not
  use them unless Rahul explicitly asks for Hinglish on a given day or group. Set `lang: en` on every
  message. No Devanagari, ever.
- **Crowd lines** only when the photo actually shows people, a queue or the cart (rule 0 above).
- **Canonical links**: use `https://theburgerlabnoida.netlify.app/` and `wa.me/919205491224`,
  not the kit's `#menu` anchor or the `?s=cl&p=a&ilr=4` tracking suffix, so copy stays identical
  everywhere.

`scripts/apply_copywriter_copy.py` re-cuts an existing queue under these rules (validates word
count, emoji count, item names, link bans; backs up the queue before writing).

## Where the facts live

- `config.js` — business info + full menu (the ONLY file to edit for site business data)
- `README.md` — setup checklist, address, group link, Google Business profile items
- `scripts/whatsapp_messages.py` — context feed generator (weather, wa_link, hours)
- `AGENTS.md` — brand hard rules
- Food court DB `menu_items` for kitchen_id=5 — live price ground truth
