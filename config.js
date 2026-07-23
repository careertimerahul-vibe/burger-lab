// ══════════════════════════════════════════════════════════════
// The Burger Lab — Configuration
// ══════════════════════════════════════════════════════════════
// This is the ONLY file you need to edit to change:
//   - Menu items, categories, prices
//   - Phone number, address, hours
//   - Tagline, review link, WhatsApp group link
//   - Any business data shown on the website
//
// After editing, deploy/re-upload index.html (it reads this file).
// ══════════════════════════════════════════════════════════════

const BURGERLAB = {

  // ── Business Info ──────────────────────────────────────────
  business: {
    name: "The Burger Lab",
    phone: "9205491224",          // without country code, no spaces
    phoneDisplay: "9205491224",   // how it appears on the site
    hours: "5PM – 1AM",
    hoursNote: "Open Daily",
    tagline: "Gourmet veg burgers, sandwiches & loaded fries — crafted fresh daily at Amrapali Golf Homes",

    address: {
      highlight: "Shop C-29",
      line2: "Amrapali Golf Homes Market",
      line3: "Haibatpur, Sector 4, Greater Noida",
      line4: "Uttar Pradesh 201016",
      mapsQuery: "The+Burger+Lab+Shop+C-29+Amrapali+Golf+Homes+Greater+Noida"
    },

    googlePlaceId: "ChIJ____T8oEDTkR",        // for review link
    whatsappGroup: "https://chat.whatsapp.com/ITnN3ll8cBiIFnEQysWuLu"
  },

  // ── Days of the Week ──────────────────────────────────────
  days: ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],

  // ── Menu ──────────────────────────────────────────────────
  // Structure: menu.{category}.{subcategory}[].{name, price, upgrade?, tag?}
  // - price: number (base price in ₹)
  // - upgrade: {price, label} — optional upgrade variant
  // - tag: string — optional tag like "Bestseller", shown as a badge
  menu: {
    burgers: {
      label: "🍔 Burgers",
      subcategories: {
        "Savory": [
          { name: "OG Alu Tikki", price: 60, upgrade: { price: 70, label: "w/ cheese" } },
          { name: "Garden Fresh Veggie", price: 80, upgrade: { price: 90 }, tag: "Bestseller" },
          { name: "Paneer Paradise", price: 100, upgrade: { price: 110 }, tag: "Bestseller" },
          { name: "Jalapeno Inferno", price: 100, upgrade: { price: 110 } },
          { name: "Double Beast", price: 120, upgrade: { price: 130 }, tag: "Bestseller" }
        ],
        "Spicy 🌶️": [
          { name: "Spicy Alu Tikki", price: 60, upgrade: { price: 70 } },
          { name: "Paneer Garden Royale", price: 130, upgrade: { price: 140 }, tag: "Bestseller" },
          { name: "Tandoori Paneer", price: 140, upgrade: { price: 150 }, tag: "Bestseller" }
        ],
        "Creamy": [
          { name: "Creamy Crispy", price: 60, upgrade: { price: 70 } },
          { name: "Makhani Paneer", price: 100, upgrade: { price: 110 } }
        ]
      }
    },

    sandwiches: {
      label: "🥪 Sandwiches",
      subcategories: {
        "Savory": [
          { name: "Veg Grilled Sandwich", price: 70, upgrade: { price: 80 } },
          { name: "Grilled Corn Sandwich", price: 80, upgrade: { price: 90 } },
          { name: "Paneer Paradise Grilled", price: 110, upgrade: { price: 120 }, tag: "Bestseller" },
          { name: "Double Decker Grilled", price: 130, upgrade: { price: 140 }, tag: "Bestseller" },
          { name: "Peppy Paneer Pizza Sandwich", price: 140 }
        ],
        "Spicy 🌶️": [
          { name: "Spicy Grilled Veg Sandwich", price: 70, upgrade: { price: 80 } },
          { name: "Tandoori Paneer Sandwich", price: 110, upgrade: { price: 120 }, tag: "Bestseller" }
        ],
        "Creamy": [
          { name: "Creamy Veggie Delight Sandwich", price: 70, upgrade: { price: 80 } }
        ]
      }
    },

    sides: {
      label: "🍟 Sides & Desserts",
      // sides are flat (no subcategories), so we use a single default subcategory
      subcategories: {
        "_": [
          { name: "French Fries (M)", price: 60 },
          { name: "French Fries (L)", price: 90 },
          { name: "Peri Peri Fries (M)", price: 80, tag: "Bestseller" },
          { name: "Peri Peri Fries (L)", price: 110, tag: "Bestseller" },
          { name: "Cheesy Fries", price: 100 },
          { name: "Spicy Masala Fries", price: 100 },
          { name: "Fully Loaded Fries", price: 130, tag: "Bestseller" },
          { name: "Stuffed Garlic Bread", price: 100, tag: "Bestseller" },
          { name: "Paneer Garlic Bread", price: 130 },
          { name: "Choco Lava Cake", price: 70 },
          { name: "Grilled Pineapple", price: 100 }
        ]
      }
    },

    combos: {
      label: "🔥 Combos",
      subcategories: {
        "_": [
          { name: "Alu Tikki + Fries + Coke", price: 130 },
          { name: "Jalapeno Inferno + Peri Peri Fries", price: 180 },
          { name: "Paneer Paradise + Jalapeno Inferno + Fries", price: 220 },
          { name: "Paneer Garden Royale + Loaded Fries", price: 240 },
          { name: "Tandoori Paneer + Loaded Fries + Coke", price: 270 },
          { name: "Make a Meal (Fries + Coke)", price: 70 }
        ]
      }
    }
  }
};
