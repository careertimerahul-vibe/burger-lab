# The Burger Lab — Cron Jobs

| Job ID | Name | Schedule | Status | Description |
|--------|------|----------|--------|-------------|
| bb3b2f1e6b39 | Burger Lab WhatsApp Messages | Daily at 5 PM IST | Active | Generates 3 WhatsApp marketing messages customized by time, weather, and weekend offers |

## Details

### Burger Lab WhatsApp Messages (bb3b2f1e6b39)
- **Schedule:** Every day at 5:00 PM IST (0 17 * * *)
- **Script:** `/opt/data/projects/burger-lab/scripts/whatsapp_messages.py`
- **Delivery:** Telegram (Rahul)
- **What it does:**
  - Checks current weather in Greater Noida
  - Detects time of day (morning/afternoon/evening/night)
  - Checks if it's a weekend
  - Generates 3 different WhatsApp-ready messages:
    1. Hook + Bestseller focus
    2. Combo Deal focus
    3. Top 3 Bestsellers focus
  - Each message includes relevant offers, weather-based hooks, and weekend specials
