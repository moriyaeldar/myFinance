"""
Transaction categorization and financial analysis engine.
"""
import re
from datetime import date, datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple

# ---------------------------------------------------------------------------
# Category rules  –  (group, category, [keyword list])
# Order matters: first match wins.
# ---------------------------------------------------------------------------
CATEGORY_RULES: List[Tuple[str, str, List[str]]] = [
    # ── Israeli merchants (checked first) ────────────────────────────────────

    # Income
    ("Income", "Salary",          ["משכורת", "שכר עבודה", "תשלום שכר", "הפקדת שכר"]),
    ("Income", "Government",      ["קצבת ילדים", "קצבה", "ביטוח לאומי", "מענק", "החזר מס", "מס הכנסה החזר"]),
    ("Income", "Transfer In",     ["bit", "פייבוקס", "paybox", "העברה", "זיכוי"]),

    # Housing
    ("Housing", "Rent / Mortgage", ["ארנונה", "ועד בית", "שכירות", "משכנתא", "טפחות", "בנק למשכנתאות"]),

    # Loans & Credit
    ("Loans & Credit", "Loan Payment",   ["הלוואה", "הו\"ק הלו", "קרן הלוואה", "ריבית הלוואה", "החזר הלוואה"]),
    ("Loans & Credit", "Credit Card",    ["מקס איט", "max it", "ישראכרט", "isracard payment", "כאל תשלום", "לאומי קארד תשלום"]),

    # Restaurants & Cafes
    ("Restaurants & Cafes", "Coffee",    ["ארומה", "aroma", "קפולסקי", "kapulsky", "קפה ג'ו", "cafe joe", "גוגל קפה", "נספרסו", "nespresso", "starbucks", "coffee"]),
    ("Restaurants & Cafes", "Fast Food", ["מקדונלד", "mcdonalds", "בורגר קינג", "burger king", "מקפלטס", "כנאפה", "שווארמה", "פלאפל", "פיצה", "pizza", "המבורגר", "BBB", "burger"]),
    ("Restaurants & Cafes", "Dining",    ["מסעדה", "restaurant", "דיינינג", "bistro", "סושי", "sushi", "קוקוריקו", "ווקו", "wolt", "וולט"]),

    # Food & Dining (groceries)
    ("Food & Dining", "Groceries", [
        "שופרסל", "shufersal", "רמי לוי", "rami levy", "ramilevi",
        "ויקטורי", "victory market", "יוחננוף", "yochananof",
        "אושר עד", "osher ad", "טיב טעם", "tiv taam",
        "am:pm", "עם פם", "מחסני השוק", "freshmarket", "supermarket",
        "grocery", "whole foods", "trader joe", "kroger", "safeway", "publix",
        "aldi", "costco", "sam's club", "wegmans", "heb",
    ]),
    ("Food & Dining", "Food Delivery", [
        "doordash", "uber eats", "grubhub", "instacart", "postmates", "seamless",
    ]),

    # Communication
    ("Communication", "Mobile",   ["סלקום", "cellcom", "פרטנר", "partner", "פלאפון", "pelephone", "הוט מובייל", "hot mobile", "012mobile", "rami-levy comm", "רמי לוי תקשורת"]),
    ("Communication", "Internet", ["בזק", "bezeq", "הוט נט", "hot net", "xfinity", "comcast", "at&t internet", "verizon fios", "cox", "spectrum"]),
    ("Communication", "TV",       ["yes", "יס", "הוט tv", "hot tv", "cable tv", "directv", "sling"]),

    # Bills & Utilities
    ("Bills & Utilities", "Electricity", ["חברת חשמל", "חח\"י", "israel electric", "electric", "pge", "con ed", "duke energy"]),
    ("Bills & Utilities", "Water",       ["מקורות", "mekorot", "תאגיד מים", "water bill", "sewage"]),
    ("Bills & Utilities", "Gas Utility", ["גז ישראל", "supergas", "paz gas", "nicor", "atmos", "gas utility"]),
    ("Bills & Utilities", "Municipality",["ארנונה", "עיריית", "מועצה מקומית"]),

    # Insurance
    ("Insurance", "Life & Health",  ["הראל ביטוח", "harel", "מגדל ביטוח", "migdal", "מנורה", "menora", "כלל ביטוח", "clal", "איילון", "הפניקס", "phoenix"]),
    ("Insurance", "Car Insurance",  ["ביטוח רכב", "שירביט", "shibrit", "direct insurance", "הכשרה ביטוח", "allianz"]),
    ("Insurance", "Home Insurance", ["ביטוח דירה", "ביטוח בית", "home insurance", "renters insurance", "geico", "allstate", "progressive", "state farm"]),

    # Transportation
    ("Transportation", "Gas & Fuel",      ["סונול", "sonol", "פז דלק", "paz", "דלק ישראל", "delek", "ten fuel", "טן", "shell", "chevron", "exxon", "bp", "fuel"]),
    ("Transportation", "Public Transit",  ["רב קו", "rav kav", "רב-קו", "ravkav", "מטרו", "רכבת", "train", "bus", "mta", "transit"]),
    ("Transportation", "Rideshare",       ["גט", "gett", "יאנגו", "yango", "uber", "lyft", "taxi", "cab"]),
    ("Transportation", "Parking",         ["חניה", "parking", "parkway", "garage"]),
    ("Transportation", "Car Maintenance", ["מוסך", "טסט", "בדיקת רכב", "oil change", "tire", "mechanic"]),
    ("Transportation", "Flights",         ["אל על", "el al", "ישראייר", "israir", "ויצ'אייר", "wizz", "ריינאייר", "ryanair", "easyjet", "delta", "united", "american airlines", "southwest"]),

    # Health & Fitness
    ("Health & Fitness", "HMO",           ["כללית", "clalit", "מכבי", "maccabi", "מאוחדת", "meuhedet", "לאומית", "leumit"]),
    ("Health & Fitness", "Pharmacy",      ["סופר פארם", "super pharm", "ניו פארם", "new pharm", "be pharm", "pharmacy", "cvs", "walgreens"]),
    ("Health & Fitness", "Dental",        ["דנטל", "dental", "שיניים", "אורתודנט", "orthodont"]),
    ("Health & Fitness", "Gym & Fitness", ["פיטנס", "fitness", "gym", "חדר כושר", "יוגה", "yoga", "pilates", "peloton", "crossfit"]),
    ("Health & Fitness", "Mental Health", ["פסיכולוג", "טיפול", "therapy", "therapist", "betterhelp"]),

    # Children & Family
    ("Children & Family", "Childcare",    ["גן ילדים", "גנון", "מעון", "צהרון", "babysitter", "daycare", "preschool", "nursery"]),
    ("Children & Family", "Kids Activities", ["ג'אנגו", "funpark", "ילדות", "toys", "צעצוע", "toysr", "the children", "ממלכה", "fun"]),
    ("Children & Family", "School",       ["בית ספר", "school", "tuition", "חינוך", "לימודים", "enrollment", "university", "college"]),
    ("Children & Family", "Baby",         ["פמפרס", "pampers", "huggies", "baby", "תינוק", "חיתול"]),

    # Clothing & Fashion
    ("Clothing & Fashion", "Clothing",    [
        "זארה", "zara", "H&M", "h&m", "גולף", "golf", "קסטרו", "castro",
        "רנואר", "renuar", "FOX", "fox", "מנגו", "mango", "טופ10", "top10",
        "פוקס", "next", "נקסט", "ביגוד", "clothing", "apparel", "fashion",
        "gap", "old navy", "banana republic", "nordstrom", "tj maxx",
    ]),
    ("Clothing & Fashion", "Shoes",       ["adidas", "nike", "new balance", "נייקי", "אדידס", "נעליים", "shoes", "foot locker"]),
    ("Clothing & Fashion", "Accessories", ["תכשיטים", "jewelry", "watches", "swatch", "pandora"]),

    # Home & Garden
    ("Home & Garden", "Furniture",       ["איקאה", "ikea", "אייס", "ace", "wayfair", "pottery barn", "west elm", "home depot", "lowes"]),
    ("Home & Garden", "Appliances",      ["שקם אלקטריק", "shakem", "כ.א.ל", "best buy", "electronics"]),
    ("Home & Garden", "Home Improvement",["אורן יצחק", "הנחת רצפה", "plumber", "electrician", "handyman", "home repair"]),
    ("Home & Garden", "Garden",          ["גינה", "garden", "plants", "צמחים"]),

    # Entertainment
    ("Entertainment", "Streaming",       ["נטפליקס", "netflix", "hulu", "disney", "hbo", "apple tv", "amazon prime", "yes vod", "hot vod"]),
    ("Entertainment", "Music",           ["spotify", "apple music", "soundcloud", "youtube music"]),
    ("Entertainment", "Gaming",          ["playstation", "xbox", "nintendo", "steam", "epic games"]),
    ("Entertainment", "Cinema & Events", ["yes planet", "יס פלאנט", "סינמה סיטי", "cinema city", "סינמטק", "cinema", "ticketmaster", "event"]),
    ("Entertainment", "Sports Events",   ["כדורגל", "כדורסל", "טדי", "בלומפילד", "סמי עופר", "hapoel", "maccabi fc"]),

    # Shopping
    ("Shopping", "Online Shopping",      ["amazon", "ebay", "aliexpress", "אליאקספרס", "etsy", "online order"]),
    ("Shopping", "General Retail",       ["target", "walmart", "dollar general", "big lots"]),
    ("Shopping", "Electronics",          ["apple store", "idigital", "ivory", "bug", "newegg", "micro center", "b&h"]),

    # Personal Care
    ("Personal Care", "Haircut & Salon", ["מספרה", "קוסמטיקה", "salon", "barber", "hair", "haircut", "great clips"]),
    ("Personal Care", "Beauty & Spa",    ["ספא", "spa", "massage", "עיסוי", "nail", "manicure", "sephora", "ulta", "beauty"]),

    # Pets
    ("Pets", "Vet & Care",   ["וטרינר", "veterinar", "vet clinic", "animal hospital"]),
    ("Pets", "Pet Food",     ["pet", "כלב", "חתול", "zoo", "petco", "petsmart", "עולם הכלב"]),

    # Gifts & Donations
    ("Gifts & Donations", "Gifts",     ["מתנה", "gift", "פרחים", "flowers", "זר פרחים"]),
    ("Gifts & Donations", "Donations", ["תרומה", "עמותה", "charity", "donation", "ידידי", "ifeel"]),

    # ATM & Cash
    ("ATM & Cash", "ATM Withdrawal", ["משיכת מזומן", "כספומט", "atm", "cash withdrawal"]),

    # Savings & Investments
    ("Savings & Investments", "Savings",     ["קרן השתלמות", "hishtalmut", "קופת גמל", "gemel", "חיסכון", "savings"]),
    ("Savings & Investments", "Pension",     ["קרן פנסיה", "פנסיה", "pension", "401k", "ira", "retirement"]),
    ("Savings & Investments", "Investments", ["בורסה", "ני\"ע", "robinhood", "fidelity", "schwab", "vanguard", "etrade", "investment", "brokerage"]),
    ("Savings & Investments", "Crypto",      ["קריפטו", "coinbase", "bitcoin", "ethereum", "binance", "crypto"]),

    # Education
    ("Education", "Tuition",         ["שכר לימוד", "אוניברסיטה", "מכללה", "tuition", "university", "college"]),
    ("Education", "Online Courses",  ["udemy", "coursera", "skillshare", "masterclass", "linkedin learning"]),
    ("Education", "Books & Supplies",["ספרים", "textbook", "school supply", "staples", "office depot"]),

    # Travel
    ("Travel", "Hotels",      ["מלון", "hotel", "marriott", "hilton", "hyatt", "airbnb", "vrbo", "inn", "resort"]),
    ("Travel", "Car Rental",  ["סיקסט", "sixt", "eldan", "אלדן", "hertz", "enterprise", "avis", "car rental"]),
    ("Travel", "Vacation",    ["expedia", "booking.com", "airbnb", "tripadvisor", "kayak", "trip", "vacation"]),

    # ── US / international income ─────────────────────────────────────────────
    ("Income", "Payroll",     ["payroll", "salary", "direct dep", "direct deposit", "ach credit", "paycheck"]),
    ("Income", "Refund",      ["refund", "cashback", "cash back", "rebate"]),
]

# Build a fast lookup
_RULES_COMPILED = [
    (group, category, [kw.lower() for kw in keywords])
    for group, category, keywords in CATEGORY_RULES
]


def categorize(description: str, merchant: str = "") -> Tuple[str, str]:
    """Return (category_group, category) for a transaction."""
    text = (description + " " + (merchant or "")).lower()

    # Strip common noise
    text = re.sub(r"\d{4,}", " ", text)   # long numbers
    text = re.sub(r"[*#]", " ", text)

    for group, category, keywords in _RULES_COMPILED:
        for kw in keywords:
            if kw in text:
                return group, category

    return "Other", "Uncategorized"


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def compute_dashboard(transactions, category_settings_map: Dict[str, str]):
    """Compute summary stats from a list of Transaction ORM objects."""
    today = date.today()
    month_start = today.replace(day=1)
    last_30 = today - timedelta(days=30)

    mtd_expenses = 0.0
    mtd_income = 0.0
    last30_expenses = 0.0
    savings_potential = 0.0
    group_totals: Dict[str, float] = defaultdict(float)

    for t in transactions:
        if t.amount > 0:
            # expense
            if t.date >= month_start:
                mtd_expenses += t.amount
            if t.date >= last_30:
                last30_expenses += t.amount
            group_totals[t.category_group] += t.amount
            # savings potential from "cut" categories
            if category_settings_map.get(t.category_group) == "cut" and t.date >= month_start:
                savings_potential += t.amount
        else:
            # income (stored as negative)
            if t.date >= month_start:
                mtd_income += abs(t.amount)

    top_cat = max(group_totals, key=group_totals.get) if group_totals else "N/A"

    return {
        "total_expenses_mtd": round(mtd_expenses, 2),
        "total_income_mtd": round(mtd_income, 2),
        "net_mtd": round(mtd_income - mtd_expenses, 2),
        "total_expenses_30d": round(last30_expenses, 2),
        "savings_potential": round(savings_potential, 2),
        "top_category": top_cat,
    }


def compute_category_summaries(transactions, settings_map: Dict[str, dict]) -> List[dict]:
    """Per-category group aggregations."""
    today = date.today()
    month_start = today.replace(day=1)

    # Determine date range for monthly average
    if transactions:
        earliest = min(t.date for t in transactions)
        months_span = max(1, ((today.year - earliest.year) * 12 + today.month - earliest.month) + 1)
    else:
        months_span = 1

    group_data: Dict[str, dict] = defaultdict(lambda: {
        "total": 0.0,
        "count": 0,
        "merchants": defaultdict(float),
    })

    total_expenses = sum(t.amount for t in transactions if t.amount > 0)

    for t in transactions:
        if t.amount <= 0:
            continue
        g = group_data[t.category_group]
        g["total"] += t.amount
        g["count"] += 1
        merchant = t.merchant_name or t.description
        g["merchants"][merchant] += t.amount

    result = []
    for group, data in group_data.items():
        setting = settings_map.get(group, {})
        top_merchants = sorted(data["merchants"], key=data["merchants"].get, reverse=True)[:3]
        result.append({
            "category_group": group,
            "total": round(data["total"], 2),
            "transaction_count": data["count"],
            "percentage_of_total": round(data["total"] / total_expenses * 100, 1) if total_expenses else 0,
            "monthly_avg": round(data["total"] / months_span, 2),
            "status": setting.get("status", "optional"),
            "monthly_budget": setting.get("monthly_budget"),
            "top_merchants": top_merchants,
        })

    return sorted(result, key=lambda x: x["total"], reverse=True)


def compute_monthly_trends(transactions) -> List[dict]:
    """Month-by-month breakdown."""
    monthly: Dict[str, dict] = defaultdict(lambda: {
        "income": 0.0,
        "expenses": 0.0,
        "by_group": defaultdict(float),
    })

    for t in transactions:
        key = t.date.strftime("%Y-%m")
        if t.amount > 0:
            monthly[key]["expenses"] += t.amount
            monthly[key]["by_group"][t.category_group] += t.amount
        else:
            monthly[key]["income"] += abs(t.amount)

    result = []
    for month in sorted(monthly.keys()):
        d = monthly[month]
        result.append({
            "month": month,
            "income": round(d["income"], 2),
            "expenses": round(d["expenses"], 2),
            "net": round(d["income"] - d["expenses"], 2),
            "by_group": {k: round(v, 2) for k, v in d["by_group"].items()},
        })

    return result[-12:]  # last 12 months
