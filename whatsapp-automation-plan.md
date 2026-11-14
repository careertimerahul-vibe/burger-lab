# WhatsApp Automation Plan — The Burger Lab

Written 2 Nov 2026. Source of truth for the outreach build. Facts verified against Meta docs + live checks (noted inline).

## Where things stand today

- **Outbound = fully manual.** Cron `bb3b2f1e6b39` (5:00 PM IST daily) generates 3 copy-paste messages + weather context and delivers them to Rahul on Telegram. Someone still opens WhatsApp and sends.
- **No API integration.** Zero Meta/Cloud API code, no WABA, no tokens, no webhook. Grep of `/opt/data` confirms nothing.
- **No customer list.** No phone numbers are captured anywhere — DB has `orders`, `funnel_events`, `sessions`, `page_views`, `pwa_installs`, `feedback` but no customer identity table. Outbound to a list is impossible until consent capture exists.
- **Assets that exist:** wa.me order link (919205491224), WhatsApp group invite, native landing page, POS + API (`api/server.py`, `source` column on orders), UTM convention `utm_source=whatsapp`.
- **Hermes' own WhatsApp channel is a Baileys linked-device bridge** (`/opt/data/scripts/whatsapp-bridge`). It *can* send to any number, but it is unofficial: bulk/unsolicited sends get the number banned and it's the number Rahul talks to the agent on. Do not use it for marketing.

## Hard limits (verified — do not plan around them)

| Thing | Reality |
|---|---|
| Posting to the existing WhatsApp group via API | **Not possible.** Groups API only creates new invite-only groups and needs an Official Business Account. Group promo stays manual. |
| Posting WhatsApp Status via API | **Not supported.** Manual. |
| Unsolicited/bulk messaging | Policy violation → quality rating drop → number restriction. Cold lists are off the table. |
| Reaching a user outside a 24h window | Only with a **pre-approved template**, and only to numbers that opted in. |
| Pricing (since 1 Jul 2025 per-message; rate card updated 1 Oct 2026) | ~₹0.86 per marketing message, ~₹0.12 utility/service, **first 1,000 service messages per number per month free**. Charged on delivery, not send. Verify final INR numbers in Billing Hub. |
| Messaging limit | New portfolio = 250 unique users / 24h. Rises to 2,000 after business verification. |
| Number choice | Coexistence now lets the same number run the WhatsApp Business app **and** Cloud API. Avoids losing the app inbox. Onboarding goes through Embedded Signup. |

## The three plays, ranked by money per rupee of effort

### Play 1 — Inbound order bot (build first, ~free to run)

Customer taps `wa.me/919205491224` → webhook → deterministic Python service (not an LLM per message) walks: menu → item + qty → pickup time → total → confirm → writes order to POS with `source='whatsapp'` + pings Rahul on Telegram. Auto-reply outside 5 PM–12 AM. Escalates to Hermes/Rahul only on unknown intent.

Why first: every unanswered message between 5 PM and 12 AM is a lost order, the cart is one person, and customer-initiated messages are free for the first 1,000/month. Zero ban risk, immediate revenue.

### Play 2 — Opt-in broadcast engine

QR at the cart + "message START for today's special" → consent row (number, timestamp, source) → 2–3 marketing templates/week to the *active* segment (ordered in last 30 days).

Cost math: 200 recipients × 8 sends/month × ₹0.86 ≈ **₹1,376/month**. Daily to the same 200 = ₹5,178/month — don't. Target: 3 sends/week, segment only recent buyers, kill any template whose quality rating drops.

### Play 3 — B2B outreach (offices, hostels, nearby societies)

Not cold-blast. One approved template, ≤50 sends/day, batch reviewed before send, aimed at offices within 3 km ordering 10+ meals. Cheaper alternative first: Google Business posts + the society groups he already sits in.

### Play 0 — today, zero approvals

Upgrade the 5 PM cron to output, per message: the WhatsApp copy, a `wa.me` tap-to-send link, and a Status caption. Build the opt-in QR + consent ledger. Tag every link `utm_source=whatsapp` so `funnel_events` attributes orders to the channel.

## Build order

1. **Play 0** — consent QR + ledger + cron output upgrade. No Meta account needed. (today)
2. **Meta setup** — Business Portfolio → FB Page → WABA → number on Coexistence → templates → billing in INR (must be migrated to INR by 31 Dec 2026 or delivery stops 1 Jan 2027).
3. **Play 1** — lead-capture bot live behind a cloudflared endpoint; POS write + Telegram ping.
4. **Play 2** — first template approved, 50-message test to Rahul's own numbers, then segment sends.
5. **Play 3** — B2B template, manual batch approval.

## What is needed from Rahul (defaults in brackets)

1. Meta Business Portfolio + a Facebook Page for The Burger Lab — admin access. [does one exist?]
2. Business verification doc — GST / Udyam / shop licence. [use shop licence + GST if registered]
3. Number: `9205491224` on **Coexistence** so the app keeps working. [recommended; needs his phone to scan the QR]
4. Card/UPI on the WABA, billing currency INR. [₹1,500/month marketing cap]
5. Existing customer numbers as CSV, if any exist anywhere (phone contacts, old orders). [none → QR opt-in is the only path]
6. Bot authority: full order-taking, or capture + hand off to Rahul to confirm? [capture + hand off for the first 2 weeks]
7. Where escalations land. [Telegram, same as today]

## Non-negotiables

- Brand is 100% vegetarian, no non-veg references, ever.
- No customer-facing send without Rahul's approval until he says otherwise.
- Prices/combos in any message come from the live menu (`menu_items`, kitchen_id=5) — never invented.
- Native landing page link only (`theburgerlabnoida.netlify.app`), not the food-court deep link.
