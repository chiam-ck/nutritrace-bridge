#!/usr/bin/env python3
"""Build a comprehensive Singapore/Malaysia local food database for NutriTrace."""

import json
import sqlite3
from datetime import datetime

DB_PATH = "/home/ck/nutritrace/data/db/nutritrace.db"

now = datetime.utcnow().isoformat() + "Z"

# All nutrition per SERVING (not per 100g)
# Format: calories(kcal), fat(g), saturated-fat(g), carbs(g), sugars(g), fiber(g), proteins(g), sodium(mg)
# extra keys like cholesterol, potassium, calcium optional

FOODS = [
    # ============================================================
    # RICE DISHES
    # ============================================================
    {
        "name": "Chicken Rice (Roasted)",
        "category": "Hawker - Rice",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 620, "fat": 22, "saturated-fat": 6, "carbohydrates": 75, "sugars": 2, "fiber": 1, "proteins": 28, "sodium": 1800},
        "notes": "Standard plate with roasted chicken, rice, cucumber, soup on side not included"
    },
    {
        "name": "Chicken Rice (Steamed / White)",
        "category": "Hawker - Rice",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 580, "fat": 18, "saturated-fat": 5, "carbohydrates": 75, "sugars": 2, "fiber": 1, "proteins": 30, "sodium": 1700},
        "notes": "Steamed/white chicken, rice, cucumber"
    },
    {
        "name": "Char Siew Rice",
        "category": "Hawker - Rice",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 650, "fat": 25, "saturated-fat": 8, "carbohydrates": 75, "sugars": 15, "fiber": 1, "proteins": 30, "sodium": 1600},
    },
    {
        "name": "Roast Duck Rice",
        "category": "Hawker - Rice",
        "portion": 420,
        "unit": "g",
        "nutrition": {"calories": 680, "fat": 28, "saturated-fat": 9, "carbohydrates": 75, "sugars": 3, "fiber": 1, "proteins": 32, "sodium": 1900},
    },
    {
        "name": "Roasted Meat Combo (Char Siew + Roast Pork + Duck)",
        "category": "Hawker - Rice",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 780, "fat": 35, "saturated-fat": 12, "carbohydrates": 78, "sugars": 10, "fiber": 1, "proteins": 38, "sodium": 2200},
    },
    {
        "name": "Economic Rice / Cai Fan (2 meat + 1 veg)",
        "category": "Hawker - Rice",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 750, "fat": 28, "saturated-fat": 8, "carbohydrates": 90, "sugars": 4, "fiber": 3, "proteins": 35, "sodium": 2000},
        "notes": "Mixed rice with 2 meat dishes, 1 vegetable, steamed rice. Varies widely."
    },
    {
        "name": "Economic Rice / Cai Fan (1 meat + 2 veg)",
        "category": "Hawker - Rice",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 580, "fat": 18, "saturated-fat": 5, "carbohydrates": 85, "sugars": 4, "fiber": 4, "proteins": 22, "sodium": 1500},
    },
    {
        "name": "Economic Rice / Cai Fan (all veg, 3 dishes)",
        "category": "Hawker - Rice",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 12, "saturated-fat": 3, "carbohydrates": 70, "sugars": 5, "fiber": 6, "proteins": 12, "sodium": 1200},
    },
    {
        "name": "Hainanese Curry Rice",
        "category": "Hawker - Rice",
        "portion": 480,
        "unit": "g",
        "nutrition": {"calories": 700, "fat": 32, "saturated-fat": 14, "carbohydrates": 80, "sugars": 4, "fiber": 2, "proteins": 28, "sodium": 2200},
        "notes": "Rice with curry gravy, braised pork, cabbage, fried pork chop"
    },
    {
        "name": "Nasi Lemak (Basic, no fried chicken)",
        "category": "Hawker - Rice",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 520, "fat": 25, "saturated-fat": 10, "carbohydrates": 60, "sugars": 3, "fiber": 2, "proteins": 16, "sodium": 1400},
        "notes": "Coconut rice, fried egg, ikan bilis, peanuts, sambal, cucumber. WITHOUT fried chicken."
    },
    {
        "name": "Nasi Lemak with Fried Chicken",
        "category": "Hawker - Rice",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 850, "fat": 45, "saturated-fat": 16, "carbohydrates": 65, "sugars": 4, "fiber": 2, "proteins": 42, "sodium": 2000},
        "notes": "Coconut rice, fried chicken drumstick/thigh, egg, ikan bilis, peanuts, sambal"
    },
    {
        "name": "Nasi Briyani (Chicken)",
        "category": "Hawker - Rice",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 780, "fat": 30, "saturated-fat": 8, "carbohydrates": 90, "sugars": 5, "fiber": 2, "proteins": 38, "sodium": 1800},
        "notes": "Briyani rice with chicken, dalcha, achar"
    },
    {
        "name": "Nasi Briyani (Mutton)",
        "category": "Hawker - Rice",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 850, "fat": 38, "saturated-fat": 14, "carbohydrates": 90, "sugars": 5, "fiber": 2, "proteins": 35, "sodium": 1900},
    },
    {
        "name": "Nasi Padang (Mixed, 2 dishes)",
        "category": "Hawker - Rice",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 750, "fat": 32, "saturated-fat": 12, "carbohydrates": 85, "sugars": 4, "fiber": 3, "proteins": 32, "sodium": 2100},
        "notes": "Steamed rice with 2 lauk (e.g., rendang + sayur lodeh). Varies by selection."
    },
    {
        "name": "Claypot Rice",
        "category": "Hawker - Rice",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 720, "fat": 22, "saturated-fat": 7, "carbohydrates": 100, "sugars": 5, "fiber": 2, "proteins": 32, "sodium": 2000},
        "notes": "Claypot chicken rice with Chinese sausage, salted fish, dark soy"
    },
    {
        "name": "Nasi Goreng (Fried Rice)",
        "category": "Hawker - Rice",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 600, "fat": 22, "saturated-fat": 5, "carbohydrates": 80, "sugars": 3, "fiber": 2, "proteins": 20, "sodium": 1800},
        "notes": "Standard fried rice with egg, vegetables, meat bits"
    },
    {
        "name": "Nasi Goreng Kampung",
        "category": "Hawker - Rice",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 580, "fat": 20, "saturated-fat": 4, "carbohydrates": 78, "sugars": 3, "fiber": 2, "proteins": 22, "sodium": 1900},
        "notes": "Spicy village-style fried rice with anchovies, kangkong, sambal"
    },
    {
        "name": "Nasi Goreng Pattaya",
        "category": "Hawker - Rice",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 700, "fat": 32, "saturated-fat": 8, "carbohydrates": 80, "sugars": 6, "fiber": 2, "proteins": 25, "sodium": 1600},
        "notes": "Fried rice wrapped in omelette, usually with chili sauce on top"
    },
    {
        "name": "Mee Goreng",
        "category": "Hawker - Rice",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 560, "fat": 22, "saturated-fat": 5, "carbohydrates": 72, "sugars": 6, "fiber": 2, "proteins": 18, "sodium": 1700},
        "notes": "Fried yellow noodles with vegetables, egg, tofu"
    },
    {
        "name": "Mee Siam",
        "category": "Hawker - Rice",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 18, "saturated-fat": 4, "carbohydrates": 65, "sugars": 8, "fiber": 2, "proteins": 15, "sodium": 1600},
        "notes": "Fried vermicelli in sweet-sour-spicy gravy, with egg, tau pok, chives"
    },
    {
        "name": "Mee Rebus",
        "category": "Hawker - Rice",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 520, "fat": 16, "saturated-fat": 3, "carbohydrates": 75, "sugars": 10, "fiber": 2, "proteins": 18, "sodium": 2000},
        "notes": "Yellow noodles in sweet potato-thickened gravy, with egg, tau pok, green chili"
    },
    {
        "name": "Fried Beehoon",
        "category": "Hawker - Rice",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 450, "fat": 16, "saturated-fat": 3, "carbohydrates": 62, "sugars": 3, "fiber": 2, "proteins": 14, "sodium": 1500},
        "notes": "Fried rice vermicelli with vegetables, egg, sometimes seafood"
    },
    {
        "name": "Fried Beehoon with Fried Chicken Wing",
        "category": "Hawker - Rice",
        "portion": 420,
        "unit": "g",
        "nutrition": {"calories": 650, "fat": 30, "saturated-fat": 7, "carbohydrates": 65, "sugars": 4, "fiber": 2, "proteins": 28, "sodium": 1800},
    },
    {
        "name": "Fried Kway Teow (Penang Style)",
        "category": "Hawker - Rice",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 520, "fat": 20, "saturated-fat": 5, "carbohydrates": 68, "sugars": 3, "fiber": 1, "proteins": 16, "sodium": 1600},
    },
    {
        "name": "Lontong",
        "category": "Hawker - Rice",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 22, "saturated-fat": 12, "carbohydrates": 55, "sugars": 5, "fiber": 3, "proteins": 14, "sodium": 1700},
        "notes": "Rice cakes in coconut gravy with vegetables, egg, sambal"
    },

    # ============================================================
    # NOODLE SOUPS
    # ============================================================
    {
        "name": "Fishball Noodles (Dry)",
        "category": "Hawker - Noodle Soup",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 12, "saturated-fat": 3, "carbohydrates": 60, "sugars": 3, "fiber": 1, "proteins": 18, "sodium": 1800},
        "notes": "Mee pok or kway teow with fishballs, fishcake, minced pork, chili-vinegar. Soup on side."
    },
    {
        "name": "Fishball Noodles (Soup)",
        "category": "Hawker - Noodle Soup",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 380, "fat": 8, "saturated-fat": 2, "carbohydrates": 58, "sugars": 2, "fiber": 1, "proteins": 20, "sodium": 2000},
    },
    {
        "name": "Bak Chor Mee (Dry)",
        "category": "Hawker - Noodle Soup",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 20, "saturated-fat": 6, "carbohydrates": 55, "sugars": 3, "fiber": 1, "proteins": 20, "sodium": 2000},
        "notes": "Mee pok with minced pork, sliced pork, pork liver, mushroom, vinegar-chili"
    },
    {
        "name": "Bak Chor Mee (Soup)",
        "category": "Hawker - Noodle Soup",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 15, "saturated-fat": 5, "carbohydrates": 55, "sugars": 2, "fiber": 1, "proteins": 20, "sodium": 2200},
    },
    {
        "name": "Laksa (Curry Laksa)",
        "category": "Hawker - Noodle Soup",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 580, "fat": 32, "saturated-fat": 18, "carbohydrates": 55, "sugars": 4, "fiber": 2, "proteins": 22, "sodium": 2200},
        "notes": "Coconut curry broth with thick rice noodles, prawns, fishcake, cockles, tau pok, bean sprouts"
    },
    {
        "name": "Asam Laksa",
        "category": "Hawker - Noodle Soup",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 380, "fat": 10, "saturated-fat": 2, "carbohydrates": 55, "sugars": 5, "fiber": 3, "proteins": 18, "sodium": 1800},
        "notes": "Tamarind-fish broth with thick rice noodles, mackerel flakes, pineapple, mint, onion, shrimp paste"
    },
    {
        "name": "Prawn Noodles / Hae Mee",
        "category": "Hawker - Noodle Soup",
        "portion": 420,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 16, "saturated-fat": 4, "carbohydrates": 62, "sugars": 3, "fiber": 1, "proteins": 24, "sodium": 2000},
        "notes": "Rich prawn-pork broth with yellow noodles, prawns, pork slices, fishcake"
    },
    {
        "name": "Lor Mee",
        "category": "Hawker - Noodle Soup",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 520, "fat": 18, "saturated-fat": 5, "carbohydrates": 70, "sugars": 4, "fiber": 1, "proteins": 22, "sodium": 2200},
        "notes": "Thick braised gravy with yellow noodles, ngoh hiang, fried fish, egg, vinegar-garlic"
    },
    {
        "name": "Beef Noodles (Dry)",
        "category": "Hawker - Noodle Soup",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 14, "saturated-fat": 4, "carbohydrates": 65, "sugars": 4, "fiber": 1, "proteins": 25, "sodium": 1800},
    },
    {
        "name": "Beef Noodles (Soup)",
        "category": "Hawker - Noodle Soup",
        "portion": 480,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 10, "saturated-fat": 3, "carbohydrates": 60, "sugars": 3, "fiber": 1, "proteins": 25, "sodium": 2000},
        "notes": "Rich beef broth with rice noodles or kway teow, sliced beef, beef balls, tripe"
    },
    {
        "name": "Ban Mian (Soup)",
        "category": "Hawker - Noodle Soup",
        "portion": 480,
        "unit": "g",
        "nutrition": {"calories": 500, "fat": 14, "saturated-fat": 3, "carbohydrates": 70, "sugars": 3, "fiber": 2, "proteins": 22, "sodium": 1900},
        "notes": "Hand-torn flat noodles in anchovy broth with minced pork, egg, ikan bilis, vegetables"
    },
    {
        "name": "Mee Soto Ayam",
        "category": "Hawker - Noodle Soup",
        "portion": 420,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 14, "saturated-fat": 3, "carbohydrates": 55, "sugars": 2, "fiber": 1, "proteins": 22, "sodium": 1800},
        "notes": "Yellow noodles in turmeric chicken broth with shredded chicken, begedil, spring onions"
    },
    {
        "name": "Yong Tau Foo (Soup, no rice)",
        "category": "Hawker - Noodle Soup",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 300, "fat": 12, "saturated-fat": 3, "carbohydrates": 25, "sugars": 4, "fiber": 5, "proteins": 22, "sodium": 1600},
        "notes": "Assorted stuffed tofu, vegetables, fish paste items in clear broth. WITHOUT noodles/rice."
    },
    {
        "name": "Yong Tau Foo (Dry with noodles)",
        "category": "Hawker - Noodle Soup",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 16, "saturated-fat": 3, "carbohydrates": 55, "sugars": 6, "fiber": 4, "proteins": 28, "sodium": 1800},
    },
    {
        "name": "Kway Chap",
        "category": "Hawker - Noodle Soup",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 600, "fat": 28, "saturated-fat": 10, "carbohydrates": 65, "sugars": 3, "fiber": 1, "proteins": 25, "sodium": 2400},
        "notes": "Broad rice sheets in dark soy broth with braised pork, intestines, tofu, egg"
    },
    {
        "name": "Sliced Fish Soup with Rice",
        "category": "Hawker - Noodle Soup",
        "portion": 550,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 8, "saturated-fat": 2, "carbohydrates": 72, "sugars": 2, "fiber": 1, "proteins": 30, "sodium": 1400},
        "notes": "Clear fish broth with sliced snakehead/batang fish, vegetables, steamed rice"
    },
    {
        "name": "Sliced Fish Beehoon Soup",
        "category": "Hawker - Noodle Soup",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 400, "fat": 8, "saturated-fat": 2, "carbohydrates": 50, "sugars": 2, "fiber": 1, "proteins": 30, "sodium": 1500},
    },
    {
        "name": "Tom Yum Soup Noodles",
        "category": "Hawker - Noodle Soup",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 14, "saturated-fat": 6, "carbohydrates": 55, "sugars": 4, "fiber": 2, "proteins": 20, "sodium": 2000},
        "notes": "Hot-sour Thai soup with rice noodles, prawns, mushrooms, lemongrass"
    },

    # ============================================================
    # FRIED & STIR-FRIED
    # ============================================================
    {
        "name": "Char Kway Teow",
        "category": "Hawker - Fried",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 650, "fat": 30, "saturated-fat": 8, "carbohydrates": 75, "sugars": 5, "fiber": 2, "proteins": 20, "sodium": 2000},
        "notes": "Stir-fried flat rice noodles with dark soy, cockles, Chinese sausage, egg, bean sprouts, lard"
    },
    {
        "name": "Char Kway Teow (Healthy / Less Oil)",
        "category": "Hawker - Fried",
        "portion": 320,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 14, "saturated-fat": 3, "carbohydrates": 60, "sugars": 4, "fiber": 2, "proteins": 16, "sodium": 1400},
    },
    {
        "name": "Hokkien Mee (Singapore, Fried Prawn)",
        "category": "Hawker - Fried",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 580, "fat": 22, "saturated-fat": 5, "carbohydrates": 70, "sugars": 4, "fiber": 2, "proteins": 25, "sodium": 2000},
        "notes": "Fried yellow noodles + bee hoon in prawn broth with prawns, squid, pork belly, sambal, lime"
    },
    {
        "name": "Hokkien Mee (KL Style, Dark)",
        "category": "Hawker - Fried",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 620, "fat": 26, "saturated-fat": 7, "carbohydrates": 75, "sugars": 6, "fiber": 2, "proteins": 22, "sodium": 2200},
        "notes": "Thick yellow noodles fried in dark soy with pork, cabbage, crackling"
    },
    {
        "name": "Fried Carrot Cake (White)",
        "category": "Hawker - Fried",
        "portion": 300,
        "unit": "g",
        "nutrition": {"calories": 500, "fat": 25, "saturated-fat": 6, "carbohydrates": 55, "sugars": 8, "fiber": 2, "proteins": 12, "sodium": 1800},
        "notes": "Steamed radish cake fried with egg, preserved radish, without dark soy"
    },
    {
        "name": "Fried Carrot Cake (Black)",
        "category": "Hawker - Fried",
        "portion": 300,
        "unit": "g",
        "nutrition": {"calories": 520, "fat": 24, "saturated-fat": 6, "carbohydrates": 58, "sugars": 10, "fiber": 2, "proteins": 12, "sodium": 2000},
        "notes": "With dark sweet soy sauce"
    },
    {
        "name": "Fried Oyster Omelette / Orh Luak",
        "category": "Hawker - Fried",
        "portion": 280,
        "unit": "g",
        "nutrition": {"calories": 550, "fat": 32, "saturated-fat": 8, "carbohydrates": 45, "sugars": 3, "fiber": 1, "proteins": 20, "sodium": 1600},
        "notes": "Oyster omelette with potato starch batter, served with chili-vinegar dip"
    },
    {
        "name": "Fried Rice with Salted Fish",
        "category": "Hawker - Fried",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 620, "fat": 22, "saturated-fat": 5, "carbohydrates": 82, "sugars": 3, "fiber": 2, "proteins": 22, "sodium": 2200},
    },
    {
        "name": "Sin Chow Mee Hoon / Singapore Beehoon",
        "category": "Hawker - Fried",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 18, "saturated-fat": 4, "carbohydrates": 62, "sugars": 4, "fiber": 2, "proteins": 18, "sodium": 1500},
        "notes": "Stir-fried vermicelli with curry powder, char siew, egg, vegetables"
    },
    {
        "name": "Mee Goreng Mamak",
        "category": "Hawker - Fried",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 600, "fat": 26, "saturated-fat": 6, "carbohydrates": 72, "sugars": 7, "fiber": 2, "proteins": 20, "sodium": 2000},
        "notes": "Indian-Muslim fried noodles with chili-tomato sauce, tofu, egg, potato, lime"
    },
    {
        "name": "Maggi Goreng",
        "category": "Hawker - Fried",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 560, "fat": 24, "saturated-fat": 5, "carbohydrates": 68, "sugars": 5, "fiber": 2, "proteins": 18, "sodium": 2200},
        "notes": "Fried instant noodles mamak style with egg, vegetables, chili"
    },

    # ============================================================
    # SNACKS & SIDES
    # ============================================================
    {
        "name": "Popiah (1 roll)",
        "category": "Hawker - Snacks",
        "portion": 150,
        "unit": "g",
        "nutrition": {"calories": 200, "fat": 8, "saturated-fat": 2, "carbohydrates": 25, "sugars": 4, "fiber": 2, "proteins": 8, "sodium": 600},
        "notes": "Fresh spring roll with turnip, egg, prawn, bean sprouts, hoisin-chili sauce"
    },
    {
        "name": "Rojak (Chinese)",
        "category": "Hawker - Snacks",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 350, "fat": 14, "saturated-fat": 2, "carbohydrates": 48, "sugars": 22, "fiber": 4, "proteins": 8, "sodium": 800},
        "notes": "Mixed fruits + dough fritters + tau pok in shrimp paste dressing with crushed peanuts"
    },
    {
        "name": "Rojak (Indian / Mamak)",
        "category": "Hawker - Snacks",
        "portion": 300,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 22, "saturated-fat": 4, "carbohydrates": 45, "sugars": 10, "fiber": 4, "proteins": 12, "sodium": 1200},
        "notes": "Fried fritters, tofu, potato, egg, cuttlefish in sweet-spicy peanut sauce"
    },
    {
        "name": "Gado-Gado",
        "category": "Hawker - Snacks",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 420, "fat": 28, "saturated-fat": 6, "carbohydrates": 30, "sugars": 8, "fiber": 5, "proteins": 16, "sodium": 1200},
        "notes": "Blanched vegetables, tofu, tempe, egg with peanut sauce dressing"
    },
    {
        "name": "Tauhu Goreng",
        "category": "Hawker - Snacks",
        "portion": 280,
        "unit": "g",
        "nutrition": {"calories": 350, "fat": 22, "saturated-fat": 4, "carbohydrates": 25, "sugars": 8, "fiber": 3, "proteins": 14, "sodium": 1100},
        "notes": "Fried tofu with bean sprouts, cucumber, sweet-spicy peanut sauce"
    },
    {
        "name": "Chwee Kueh (4 pieces)",
        "category": "Hawker - Snacks",
        "portion": 200,
        "unit": "g",
        "nutrition": {"calories": 280, "fat": 8, "saturated-fat": 2, "carbohydrates": 45, "sugars": 2, "fiber": 1, "proteins": 6, "sodium": 900},
        "notes": "Steamed rice cakes topped with preserved radish (chai po) and sambal"
    },
    {
        "name": "Chee Cheong Fun (Plain, with sweet sauce)",
        "category": "Hawker - Snacks",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 280, "fat": 6, "saturated-fat": 1, "carbohydrates": 50, "sugars": 10, "fiber": 1, "proteins": 6, "sodium": 700},
        "notes": "Steamed rice noodle rolls with sweet soy, sesame oil, sesame seeds"
    },
    {
        "name": "Chee Cheong Fun (with Char Siew)",
        "category": "Hawker - Snacks",
        "portion": 280,
        "unit": "g",
        "nutrition": {"calories": 380, "fat": 14, "saturated-fat": 4, "carbohydrates": 48, "sugars": 8, "fiber": 1, "proteins": 16, "sodium": 900},
    },
    {
        "name": "Curry Puff (1 piece)",
        "category": "Hawker - Snacks",
        "portion": 80,
        "unit": "g",
        "nutrition": {"calories": 220, "fat": 14, "saturated-fat": 5, "carbohydrates": 20, "sugars": 2, "fiber": 1, "proteins": 4, "sodium": 350},
        "notes": "Deep-fried pastry with curried potato and chicken filling"
    },
    {
        "name": "Spring Roll / Popiah Goreng (1 piece)",
        "category": "Hawker - Snacks",
        "portion": 70,
        "unit": "g",
        "nutrition": {"calories": 150, "fat": 10, "saturated-fat": 3, "carbohydrates": 12, "sugars": 2, "fiber": 1, "proteins": 3, "sodium": 300},
    },
    {
        "name": "Otak-Otak (1 piece)",
        "category": "Hawker - Snacks",
        "portion": 60,
        "unit": "g",
        "nutrition": {"calories": 90, "fat": 6, "saturated-fat": 3, "carbohydrates": 4, "sugars": 1, "fiber": 0, "proteins": 6, "sodium": 350},
        "notes": "Grilled spiced fish paste in banana leaf"
    },
    {
        "name": "Satay - Chicken (10 sticks)",
        "category": "Hawker - Snacks",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 480, "fat": 25, "saturated-fat": 8, "carbohydrates": 15, "sugars": 10, "fiber": 1, "proteins": 48, "sodium": 1200},
        "notes": "Grilled marinated chicken skewers with peanut sauce, ketupat, onion, cucumber"
    },
    {
        "name": "Satay - Beef (10 sticks)",
        "category": "Hawker - Snacks",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 520, "fat": 28, "saturated-fat": 10, "carbohydrates": 15, "sugars": 10, "fiber": 1, "proteins": 45, "sodium": 1300},
    },
    {
        "name": "Satay - Mutton (10 sticks)",
        "category": "Hawker - Snacks",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 550, "fat": 32, "saturated-fat": 12, "carbohydrates": 15, "sugars": 10, "fiber": 1, "proteins": 42, "sodium": 1300},
    },

    # ============================================================
    # MALAY DISHES (sides / lauk)
    # ============================================================
    {
        "name": "Rendang (Beef, 1 serving)",
        "category": "Malay Dishes",
        "portion": 150,
        "unit": "g",
        "nutrition": {"calories": 320, "fat": 24, "saturated-fat": 10, "carbohydrates": 6, "sugars": 3, "fiber": 1, "proteins": 22, "sodium": 800},
        "notes": "Slow-cooked beef in coconut-spice paste. Side dish portion."
    },
    {
        "name": "Rendang (Chicken, 1 serving)",
        "category": "Malay Dishes",
        "portion": 150,
        "unit": "g",
        "nutrition": {"calories": 280, "fat": 20, "saturated-fat": 8, "carbohydrates": 5, "sugars": 2, "fiber": 1, "proteins": 20, "sodium": 700},
    },
    {
        "name": "Sambal Sotong (1 serving)",
        "category": "Malay Dishes",
        "portion": 120,
        "unit": "g",
        "nutrition": {"calories": 180, "fat": 8, "saturated-fat": 2, "carbohydrates": 10, "sugars": 5, "fiber": 1, "proteins": 18, "sodium": 900},
        "notes": "Squid in spicy sambal sauce"
    },
    {
        "name": "Sambal Prawns (1 serving)",
        "category": "Malay Dishes",
        "portion": 120,
        "unit": "g",
        "nutrition": {"calories": 200, "fat": 10, "saturated-fat": 2, "carbohydrates": 8, "sugars": 5, "fiber": 1, "proteins": 20, "sodium": 900},
    },
    {
        "name": "Sayur Lodeh (1 serving)",
        "category": "Malay Dishes",
        "portion": 200,
        "unit": "g",
        "nutrition": {"calories": 180, "fat": 14, "saturated-fat": 8, "carbohydrates": 12, "sugars": 4, "fiber": 4, "proteins": 6, "sodium": 600},
        "notes": "Mixed vegetables in coconut milk broth"
    },
    {
        "name": "Ayam Goreng Berempah (1 piece)",
        "category": "Malay Dishes",
        "portion": 150,
        "unit": "g",
        "nutrition": {"calories": 350, "fat": 24, "saturated-fat": 6, "carbohydrates": 8, "sugars": 1, "fiber": 0, "proteins": 26, "sodium": 700},
        "notes": "Spiced fried chicken with rempah coating"
    },
    {
        "name": "Ikan Bakar (1 serving with sambal)",
        "category": "Malay Dishes",
        "portion": 200,
        "unit": "g",
        "nutrition": {"calories": 280, "fat": 16, "saturated-fat": 4, "carbohydrates": 6, "sugars": 3, "fiber": 1, "proteins": 28, "sodium": 900},
        "notes": "Grilled fish (stingray/parang) with sambal, wrapped in banana leaf"
    },
    {
        "name": "Ayam Percik (1 piece)",
        "category": "Malay Dishes",
        "portion": 180,
        "unit": "g",
        "nutrition": {"calories": 380, "fat": 26, "saturated-fat": 10, "carbohydrates": 10, "sugars": 6, "fiber": 1, "proteins": 28, "sodium": 800},
        "notes": "Grilled chicken with creamy spiced coconut sauce"
    },
    {
        "name": "Kangkong Belacan (1 serving)",
        "category": "Malay Dishes",
        "portion": 150,
        "unit": "g",
        "nutrition": {"calories": 80, "fat": 5, "saturated-fat": 1, "carbohydrates": 6, "sugars": 2, "fiber": 3, "proteins": 4, "sodium": 600},
        "notes": "Water spinach stir-fried with shrimp paste and chili"
    },
    {
        "name": "Tempe Goreng (1 serving)",
        "category": "Malay Dishes",
        "portion": 80,
        "unit": "g",
        "nutrition": {"calories": 180, "fat": 12, "saturated-fat": 2, "carbohydrates": 8, "sugars": 1, "fiber": 3, "proteins": 12, "sodium": 300},
        "notes": "Deep-fried fermented soybean cake"
    },

    # ============================================================
    # INDIAN / MAMAK DISHES
    # ============================================================
    {
        "name": "Roti Prata (Plain, 1 piece)",
        "category": "Indian / Mamak",
        "portion": 90,
        "unit": "g",
        "nutrition": {"calories": 280, "fat": 12, "saturated-fat": 5, "carbohydrates": 35, "sugars": 1, "fiber": 1, "proteins": 7, "sodium": 500},
        "notes": "Without curry or sugar. Add curry separately."
    },
    {
        "name": "Roti Prata (Egg, 1 piece)",
        "category": "Indian / Mamak",
        "portion": 120,
        "unit": "g",
        "nutrition": {"calories": 360, "fat": 18, "saturated-fat": 6, "carbohydrates": 35, "sugars": 2, "fiber": 1, "proteins": 14, "sodium": 600},
    },
    {
        "name": "Roti Prata (2 plain + curry)",
        "category": "Indian / Mamak",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 620, "fat": 28, "saturated-fat": 12, "carbohydrates": 75, "sugars": 4, "fiber": 3, "proteins": 16, "sodium": 1200},
        "notes": "2 plain prata with dhal/fish curry"
    },
    {
        "name": "Murtabak (Chicken, 1 piece)",
        "category": "Indian / Mamak",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 750, "fat": 38, "saturated-fat": 14, "carbohydrates": 65, "sugars": 4, "fiber": 2, "proteins": 35, "sodium": 1800},
        "notes": "Stuffed pan-fried bread with spiced minced chicken, egg, onion. Usually shared."
    },
    {
        "name": "Thosai (Plain, 1 piece)",
        "category": "Indian / Mamak",
        "portion": 120,
        "unit": "g",
        "nutrition": {"calories": 200, "fat": 3, "saturated-fat": 0.5, "carbohydrates": 38, "sugars": 1, "fiber": 2, "proteins": 6, "sodium": 300},
        "notes": "Fermented rice-lentil crepe. Served with dhal, chutney, sambar."
    },
    {
        "name": "Masala Thosai (1 piece)",
        "category": "Indian / Mamak",
        "portion": 200,
        "unit": "g",
        "nutrition": {"calories": 350, "fat": 10, "saturated-fat": 2, "carbohydrates": 52, "sugars": 3, "fiber": 3, "proteins": 12, "sodium": 600},
        "notes": "Thosai with spiced potato filling"
    },
    {
        "name": "Idli (2 pieces with sambar)",
        "category": "Indian / Mamak",
        "portion": 300,
        "unit": "g",
        "nutrition": {"calories": 250, "fat": 3, "saturated-fat": 0.5, "carbohydrates": 48, "sugars": 3, "fiber": 4, "proteins": 10, "sodium": 600},
        "notes": "Steamed rice-lentil cakes with sambar and chutney"
    },
    {
        "name": "Vadai (1 piece)",
        "category": "Indian / Mamak",
        "portion": 60,
        "unit": "g",
        "nutrition": {"calories": 150, "fat": 8, "saturated-fat": 1, "carbohydrates": 18, "sugars": 1, "fiber": 2, "proteins": 4, "sodium": 300},
        "notes": "Deep-fried lentil donut"
    },
    {
        "name": "Roti John",
        "category": "Indian / Mamak",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 550, "fat": 30, "saturated-fat": 8, "carbohydrates": 45, "sugars": 6, "fiber": 2, "proteins": 25, "sodium": 1200},
        "notes": "Toasted baguette with minced meat-egg omelette, chili-mayo sauce"
    },
    {
        "name": "Nasi Kandar (Mixed rice with 2 curries)",
        "category": "Indian / Mamak",
        "portion": 500,
        "unit": "g",
        "nutrition": {"calories": 800, "fat": 35, "saturated-fat": 12, "carbohydrates": 90, "sugars": 5, "fiber": 2, "proteins": 35, "sodium": 2200},
        "notes": "Steamed rice with mixed curries. Very variable."
    },
    {
        "name": "Chicken Tandoori (2 pieces, with onion)",
        "category": "Indian / Mamak",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 350, "fat": 18, "saturated-fat": 5, "carbohydrates": 6, "sugars": 3, "fiber": 1, "proteins": 42, "sodium": 800},
    },
    {
        "name": "Butter Chicken with Rice",
        "category": "Indian / Mamak",
        "portion": 450,
        "unit": "g",
        "nutrition": {"calories": 700, "fat": 32, "saturated-fat": 14, "carbohydrates": 72, "sugars": 6, "fiber": 2, "proteins": 32, "sodium": 1500},
    },
    {
        "name": "Appam (2 pieces)",
        "category": "Indian / Mamak",
        "portion": 150,
        "unit": "g",
        "nutrition": {"calories": 250, "fat": 6, "saturated-fat": 3, "carbohydrates": 42, "sugars": 6, "fiber": 1, "proteins": 5, "sodium": 200},
        "notes": "Fermented rice-coconut crepe with crispy edges. Usually with coconut milk or gula melaka."
    },

    # ============================================================
    # KUEH & DESSERTS
    # ============================================================
    {
        "name": "Chendol",
        "category": "Kueh & Desserts",
        "portion": 300,
        "unit": "g",
        "nutrition": {"calories": 320, "fat": 14, "saturated-fat": 10, "carbohydrates": 45, "sugars": 30, "fiber": 1, "proteins": 4, "sodium": 150},
        "notes": "Shaved ice with green rice flour jelly, coconut milk, gula melaka, red bean"
    },
    {
        "name": "Ice Kachang",
        "category": "Kueh & Desserts",
        "portion": 350,
        "unit": "g",
        "nutrition": {"calories": 350, "fat": 6, "saturated-fat": 2, "carbohydrates": 70, "sugars": 45, "fiber": 2, "proteins": 6, "sodium": 150},
        "notes": "Shaved ice with red bean, corn, attap chee, jelly, condensed milk, syrup"
    },
    {
        "name": "Bubur Cha Cha",
        "category": "Kueh & Desserts",
        "portion": 300,
        "unit": "g",
        "nutrition": {"calories": 300, "fat": 14, "saturated-fat": 10, "carbohydrates": 40, "sugars": 18, "fiber": 2, "proteins": 4, "sodium": 150},
        "notes": "Sweet coconut soup with yam, sweet potato, tapioca jelly, sago"
    },
    {
        "name": "Pulut Hitam",
        "category": "Kueh & Desserts",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 300, "fat": 8, "saturated-fat": 5, "carbohydrates": 52, "sugars": 18, "fiber": 3, "proteins": 5, "sodium": 100},
        "notes": "Black glutinous rice porridge with coconut milk"
    },
    {
        "name": "Tau Huay / Soya Beancurd",
        "category": "Kueh & Desserts",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 150, "fat": 4, "saturated-fat": 1, "carbohydrates": 22, "sugars": 18, "fiber": 0, "proteins": 8, "sodium": 50},
        "notes": "Silken soya beancurd in sugar syrup"
    },
    {
        "name": "Tau Suan",
        "category": "Kueh & Desserts",
        "portion": 250,
        "unit": "g",
        "nutrition": {"calories": 250, "fat": 2, "saturated-fat": 0.5, "carbohydrates": 55, "sugars": 25, "fiber": 2, "proteins": 5, "sodium": 50},
        "notes": "Split mung bean sweet soup with fried dough stick (you tiao)"
    },
    {
        "name": "Ondeh-Ondeh (3 pieces)",
        "category": "Kueh & Desserts",
        "portion": 90,
        "unit": "g",
        "nutrition": {"calories": 180, "fat": 6, "saturated-fat": 3, "carbohydrates": 30, "sugars": 14, "fiber": 1, "proteins": 2, "sodium": 30},
        "notes": "Glutinous rice balls filled with gula melaka, coated in coconut"
    },
    {
        "name": "Kueh Lapis (2 pieces)",
        "category": "Kueh & Desserts",
        "portion": 100,
        "unit": "g",
        "nutrition": {"calories": 200, "fat": 8, "saturated-fat": 4, "carbohydrates": 30, "sugars": 18, "fiber": 0, "proteins": 3, "sodium": 100},
        "notes": "Steamed layered rice flour cake with coconut milk"
    },
    {
        "name": "Apam Balik (1 piece)",
        "category": "Kueh & Desserts",
        "portion": 120,
        "unit": "g",
        "nutrition": {"calories": 350, "fat": 16, "saturated-fat": 4, "carbohydrates": 45, "sugars": 20, "fiber": 2, "proteins": 8, "sodium": 200},
        "notes": "Malaysian-style thick pancake with crushed peanuts, sugar, creamed corn"
    },
    {
        "name": "Pisang Goreng (3 pieces)",
        "category": "Kueh & Desserts",
        "portion": 150,
        "unit": "g",
        "nutrition": {"calories": 320, "fat": 16, "saturated-fat": 4, "carbohydrates": 42, "sugars": 18, "fiber": 3, "proteins": 3, "sodium": 150},
        "notes": "Deep-fried battered banana fritters"
    },
    {
        "name": "Muah Chee (1 serving)",
        "category": "Kueh & Desserts",
        "portion": 100,
        "unit": "g",
        "nutrition": {"calories": 250, "fat": 6, "saturated-fat": 1, "carbohydrates": 45, "sugars": 12, "fiber": 1, "proteins": 3, "sodium": 50},
        "notes": "Glutinous rice dough coated in crushed peanut-sugar"
    },
    {
        "name": "Kueh Dadar (1 piece)",
        "category": "Kueh & Desserts",
        "portion": 80,
        "unit": "g",
        "nutrition": {"calories": 160, "fat": 8, "saturated-fat": 5, "carbohydrates": 20, "sugars": 10, "fiber": 1, "proteins": 2, "sodium": 80},
        "notes": "Pandan crepe with grated coconut-gula melaka filling"
    },
    {
        "name": "Ang Ku Kueh (1 piece)",
        "category": "Kueh & Desserts",
        "portion": 60,
        "unit": "g",
        "nutrition": {"calories": 120, "fat": 2, "saturated-fat": 0.5, "carbohydrates": 24, "sugars": 6, "fiber": 1, "proteins": 2, "sodium": 40},
        "notes": "Red tortoise-shell glutinous rice cake with mung bean or peanut filling"
    },

    # ============================================================
    # DRINKS (HOT)
    # ============================================================
    {
        "name": "Kopi O (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 55, "fat": 0, "saturated-fat": 0, "carbohydrates": 13, "sugars": 12, "fiber": 0, "proteins": 0, "sodium": 5},
        "notes": "Black coffee with sugar. Nanyang-style robusta brew."
    },
    {
        "name": "Kopi O Kosong (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 5, "fat": 0, "saturated-fat": 0, "carbohydrates": 1, "sugars": 0, "fiber": 0, "proteins": 0, "sodium": 5},
        "notes": "Black coffee, no sugar"
    },
    {
        "name": "Kopi (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 80, "fat": 2, "saturated-fat": 1, "carbohydrates": 14, "sugars": 12, "fiber": 0, "proteins": 1, "sodium": 10},
        "notes": "Coffee with condensed milk and sugar"
    },
    {
        "name": "Kopi C (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 65, "fat": 2, "saturated-fat": 1, "carbohydrates": 12, "sugars": 10, "fiber": 0, "proteins": 1, "sodium": 15},
        "notes": "Coffee with evaporated milk and sugar"
    },
    {
        "name": "Kopi C Kosong (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 20, "fat": 2, "saturated-fat": 1, "carbohydrates": 2, "sugars": 1, "fiber": 0, "proteins": 1, "sodium": 15},
        "notes": "Coffee with evaporated milk, no sugar"
    },
    {
        "name": "Teh O (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 45, "fat": 0, "saturated-fat": 0, "carbohydrates": 11, "sugars": 11, "fiber": 0, "proteins": 0, "sodium": 5},
        "notes": "Black tea with sugar"
    },
    {
        "name": "Teh O Kosong (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 2, "fat": 0, "saturated-fat": 0, "carbohydrates": 0.5, "sugars": 0, "fiber": 0, "proteins": 0, "sodium": 5},
        "notes": "Black tea, no sugar, no milk"
    },
    {
        "name": "Teh (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 75, "fat": 2, "saturated-fat": 1, "carbohydrates": 13, "sugars": 12, "fiber": 0, "proteins": 1, "sodium": 10},
        "notes": "Tea with condensed milk and sugar"
    },
    {
        "name": "Teh C (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 60, "fat": 2, "saturated-fat": 1, "carbohydrates": 11, "sugars": 10, "fiber": 0, "proteins": 1, "sodium": 15},
        "notes": "Tea with evaporated milk and sugar"
    },
    {
        "name": "Teh C Kosong (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 18, "fat": 2, "saturated-fat": 1, "carbohydrates": 1, "sugars": 1, "fiber": 0, "proteins": 1, "sodium": 15},
        "notes": "Tea with evaporated milk, no sugar"
    },
    {
        "name": "Teh Halia (Hot)",
        "category": "Drinks - Hot",
        "portion": 200,
        "unit": "ml",
        "nutrition": {"calories": 70, "fat": 2, "saturated-fat": 1, "carbohydrates": 12, "sugars": 11, "fiber": 0, "proteins": 1, "sodium": 10},
        "notes": "Tea with ginger, condensed milk and sugar"
    },
    {
        "name": "Milo (Hot, standard)",
        "category": "Drinks - Hot",
        "portion": 250,
        "unit": "ml",
        "nutrition": {"calories": 180, "fat": 4, "saturated-fat": 2, "carbohydrates": 30, "sugars": 22, "fiber": 1, "proteins": 6, "sodium": 80},
        "notes": "Milo with condensed milk and sugar. Kopitiam style."
    },
    {
        "name": "Horlicks (Hot)",
        "category": "Drinks - Hot",
        "portion": 250,
        "unit": "ml",
        "nutrition": {"calories": 160, "fat": 3, "saturated-fat": 2, "carbohydrates": 28, "sugars": 20, "fiber": 0, "proteins": 5, "sodium": 80},
    },

    # ============================================================
    # DRINKS (COLD)
    # ============================================================
    {
        "name": "Teh Tarik (Hot)",
        "category": "Drinks - Hot",
        "portion": 250,
        "unit": "ml",
        "nutrition": {"calories": 100, "fat": 3, "saturated-fat": 2, "carbohydrates": 16, "sugars": 14, "fiber": 0, "proteins": 2, "sodium": 15},
        "notes": "Pulled tea with condensed milk"
    },
    {
        "name": "Teh Tarik (Iced)",
        "category": "Drinks - Cold",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 120, "fat": 3, "saturated-fat": 2, "carbohydrates": 20, "sugars": 18, "fiber": 0, "proteins": 2, "sodium": 15},
    },
    {
        "name": "Kopi Peng / Iced Coffee",
        "category": "Drinks - Cold",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 100, "fat": 2, "saturated-fat": 1, "carbohydrates": 20, "sugars": 18, "fiber": 0, "proteins": 1, "sodium": 15},
    },
    {
        "name": "Teh Peng / Iced Tea",
        "category": "Drinks - Cold",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 90, "fat": 2, "saturated-fat": 1, "carbohydrates": 18, "sugars": 16, "fiber": 0, "proteins": 1, "sodium": 15},
    },
    {
        "name": "Milo Dinosaur",
        "category": "Drinks - Cold",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 260, "fat": 8, "saturated-fat": 4, "carbohydrates": 40, "sugars": 32, "fiber": 1, "proteins": 8, "sodium": 100},
        "notes": "Iced Milo with extra Milo powder on top"
    },
    {
        "name": "Milo Peng / Iced Milo",
        "category": "Drinks - Cold",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 200, "fat": 5, "saturated-fat": 3, "carbohydrates": 32, "sugars": 25, "fiber": 1, "proteins": 6, "sodium": 80},
    },
    {
        "name": "Bandung",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 150, "fat": 2, "saturated-fat": 1, "carbohydrates": 32, "sugars": 28, "fiber": 0, "proteins": 2, "sodium": 30},
        "notes": "Rose syrup with evaporated milk"
    },
    {
        "name": "Sugarcane Juice (with lemon)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 180, "fat": 0, "saturated-fat": 0, "carbohydrates": 45, "sugars": 42, "fiber": 0, "proteins": 0, "sodium": 10},
        "notes": "Fresh pressed sugarcane juice. High natural sugar."
    },
    {
        "name": "Soya Bean Milk (no sugar)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 90, "fat": 3, "saturated-fat": 0.5, "carbohydrates": 6, "sugars": 3, "fiber": 1, "proteins": 10, "sodium": 15},
    },
    {
        "name": "Soya Bean Milk (with sugar)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 150, "fat": 3, "saturated-fat": 0.5, "carbohydrates": 22, "sugars": 18, "fiber": 1, "proteins": 10, "sodium": 15},
    },
    {
        "name": "Chin Chow Drink",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 120, "fat": 0, "saturated-fat": 0, "carbohydrates": 30, "sugars": 28, "fiber": 0, "proteins": 0, "sodium": 10},
        "notes": "Grass jelly drink with sugar syrup"
    },
    {
        "name": "Lime Juice (Iced)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 70, "fat": 0, "saturated-fat": 0, "carbohydrates": 18, "sugars": 16, "fiber": 0, "proteins": 0, "sodium": 5},
        "notes": "Fresh lime juice with sugar syrup"
    },
    {
        "name": "Lime Juice (Unsweetened)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 10, "fat": 0, "saturated-fat": 0, "carbohydrates": 2, "sugars": 0, "fiber": 0, "proteins": 0, "sodium": 5},
    },
    {
        "name": "Barley Water (Iced)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 80, "fat": 0, "saturated-fat": 0, "carbohydrates": 20, "sugars": 16, "fiber": 0, "proteins": 0, "sodium": 10},
        "notes": "Boiled pearl barley drink with sugar. Good for cooling."
    },
    {
        "name": "Cheng Tng",
        "category": "Drinks - Cold",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 200, "fat": 1, "saturated-fat": 0, "carbohydrates": 48, "sugars": 32, "fiber": 2, "proteins": 2, "sodium": 30},
        "notes": "Sweet dessert soup with dried longan, barley, ginkgo, lotus seed, jelly. Cold or hot."
    },
    {
        "name": "Coconut Water (Fresh, whole coconut)",
        "category": "Drinks - Cold",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 65, "fat": 0.5, "saturated-fat": 0.5, "carbohydrates": 15, "sugars": 12, "fiber": 1, "proteins": 2, "sodium": 80, "potassium": 600},
    },
    {
        "name": "Sirap Bandung (Plain, no milk)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 120, "fat": 0, "saturated-fat": 0, "carbohydrates": 30, "sugars": 28, "fiber": 0, "proteins": 0, "sodium": 10},
    },
    {
        "name": "Calamansi Juice (Iced)",
        "category": "Drinks - Cold",
        "portion": 300,
        "unit": "ml",
        "nutrition": {"calories": 80, "fat": 0, "saturated-fat": 0, "carbohydrates": 20, "sugars": 18, "fiber": 0, "proteins": 0, "sodium": 5},
    },

    # ============================================================
    # WESTERN (HAWKER STYLE)
    # ============================================================
    {
        "name": "Chicken Chop (Hawker style, with fries + coleslaw)",
        "category": "Western (Hawker)",
        "portion": 400,
        "unit": "g",
        "nutrition": {"calories": 700, "fat": 35, "saturated-fat": 10, "carbohydrates": 60, "sugars": 8, "fiber": 3, "proteins": 35, "sodium": 1500},
        "notes": "Pan-fried chicken chop with brown sauce, fries, coleslaw, baked beans"
    },
    {
        "name": "Fish and Chips (Hawker style)",
        "category": "Western (Hawker)",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 650, "fat": 32, "saturated-fat": 6, "carbohydrates": 60, "sugars": 4, "fiber": 2, "proteins": 28, "sodium": 1200},
        "notes": "Battered fish fillet with fries, tartar sauce, coleslaw"
    },
    {
        "name": "Chicken Cutlet Rice",
        "category": "Western (Hawker)",
        "portion": 420,
        "unit": "g",
        "nutrition": {"calories": 680, "fat": 28, "saturated-fat": 7, "carbohydrates": 75, "sugars": 4, "fiber": 2, "proteins": 32, "sodium": 1400},
        "notes": "Fried breaded chicken cutlet with rice, brown sauce, sunny side up egg"
    },
    {
        "name": "Pork Chop (Hawker style)",
        "category": "Western (Hawker)",
        "portion": 380,
        "unit": "g",
        "nutrition": {"calories": 650, "fat": 32, "saturated-fat": 10, "carbohydrates": 55, "sugars": 5, "fiber": 2, "proteins": 35, "sodium": 1600},
        "notes": "Pan-fried pork chop with fries, coleslaw, brown sauce"
    },

    # ============================================================
    # SOUPS (light meals)
    # ============================================================
    {
        "name": "ABC Soup (1 bowl)",
        "category": "Soup",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 120, "fat": 3, "saturated-fat": 1, "carbohydrates": 15, "sugars": 6, "fiber": 3, "proteins": 10, "sodium": 500},
        "notes": "Carrot, potato, tomato, onion, pork rib soup"
    },
    {
        "name": "Lotus Root Soup with Pork Ribs (1 bowl)",
        "category": "Soup",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 150, "fat": 6, "saturated-fat": 2, "carbohydrates": 12, "sugars": 4, "fiber": 2, "proteins": 12, "sodium": 600},
    },
    {
        "name": "Watercress Soup (1 bowl)",
        "category": "Soup",
        "portion": 350,
        "unit": "ml",
        "nutrition": {"calories": 80, "fat": 2, "saturated-fat": 0.5, "carbohydrates": 8, "sugars": 2, "fiber": 2, "proteins": 8, "sodium": 500},
    },

    # ============================================================
    # CONDIMENTS & SIDES  
    # ============================================================
    {
        "name": "Steamed White Rice (1 bowl)",
        "category": "Staples",
        "portion": 200,
        "unit": "g",
        "nutrition": {"calories": 260, "fat": 0.5, "saturated-fat": 0.1, "carbohydrates": 58, "sugars": 0, "fiber": 1, "proteins": 5, "sodium": 5},
    },
    {
        "name": "Coconut Rice (1 serving)",
        "category": "Staples",
        "portion": 200,
        "unit": "g",
        "nutrition": {"calories": 320, "fat": 12, "saturated-fat": 8, "carbohydrates": 48, "sugars": 1, "fiber": 1, "proteins": 5, "sodium": 200},
        "notes": "Nasi lemak rice cooked with coconut milk and pandan"
    },
]

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    
    inserted = 0
    for food in FOODS:
        name = food["name"]
        category = food.get("category")
        portion = food.get("portion", 100)
        unit = food.get("unit", "g")
        nutrition = json.dumps(food.get("nutrition", {}))
        notes = food.get("notes")
        
        # Check if already exists (by name)
        existing = conn.execute(
            "SELECT id FROM foods WHERE name = ? AND user_id IS NULL AND deleted_at IS NULL",
            (name,)
        ).fetchone()
        
        if existing:
            continue
        
        conn.execute(
            """INSERT INTO foods (user_id, name, brand, nutrition, portion, unit, img_url, notes, 
               category, created_at, updated_at, visibility)
               VALUES (NULL, ?, NULL, ?, ?, ?, NULL, ?, ?, ?, ?, 'private')""",
            (name, nutrition, portion, unit, notes, category, now, now)
        )
        inserted += 1
    
    conn.commit()
    conn.close()
    print(f"✅ Inserted {inserted} new foods. Total foods defined: {len(FOODS)}")

if __name__ == "__main__":
    main()
