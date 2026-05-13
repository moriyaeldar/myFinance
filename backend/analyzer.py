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
    ("Income", "Salary", ["משכורת", "שכר עבודה", "תשלום שכר", "הפקדת שכר"]),

    # Housing
    ("Housing", "Rent / Mortgage", ["ארנונה", "ועד בית", "שכירות", "משכנתא"]),

    # Food & Dining
    ("Food & Dining", "Groceries", [
        "שופרסל", "shufersal", "רמי לוי", "rami levy", "ramilevi",
        "ויקטורי", "victory market", "יוחננוף", "yochananof",
        "אושר עד", "osher ad", "טיב טעם", "tiv taam",
        "am:pm", "עם פם", "מחסני השוק",
    ]),
    ("Food & Dining", "Restaurants", ["קפה", "מסעדה", "פיצה", "המבורגר", "שווארמה", "פלאפל"]),

    # Transportation
    ("Transportation", "Gas & Fuel", ["סונול", "sonol", "פז דלק", "paz fuel", "דלק ישראל", "delek", "ten fuel", "טן פול"]),
    ("Transportation", "Public Transit", ["רב קו", "rav kav", "רב-קו", "ravkav"]),
    ("Transportation", "Rideshare", ["גט טקסי", "gett", "יאנגו", "yango"]),

    # Bills & Utilities
    ("Bills & Utilities", "Electricity", ["חברת חשמל", "חח\"י", "israel electric"]),
    ("Bills & Utilities", "Water", ["מקורות", "mekorot", "תאגיד מים"]),
    ("Bills & Utilities", "Phone", [
        "בזק", "bezeq", "פרטנר", "partner comm", "סלקום", "cellcom",
        "הוט מובייל", "hot mobile", "פלאפון", "pelephone",
    ]),
    ("Bills & Utilities", "Insurance", [
        "הראל ביטוח", "harel", "מגדל ביטוח", "migdal",
        "מנורה מבטחים", "menora", "כלל ביטוח", "clal insurance",
        "איילון ביטוח", "הפניקס", "phoenix insurance",
    ]),

    # Health & Fitness
    ("Health & Fitness", "Doctor / Hospital", [
        "כללית", "clalit", "מכבי", "maccabi health", "מאוחדת", "meuhedet",
        "לאומית בריאות", "leumit health",
    ]),
    ("Health & Fitness", "Pharmacy", ["סופר פארם", "super pharm", "ניו פארם", "new pharm", "be pharm"]),

    # Entertainment
    ("Entertainment", "Movies & Events", ["yes planet", "יס פלאנט", "סינמה סיטי", "cinema city", "סינמטק"]),

    # Savings & Investments
    ("Savings & Investments", "Retirement", [
        "קרן פנסיה", "פנסיה", "קרן השתלמות", "hishtalmut", "קופת גמל", "gemel",
    ]),

    # ── US / international merchants ─────────────────────────────────────────
    # Income
    ("Income", "Payroll", ["payroll", "salary", "direct dep", "direct deposit", "ach credit", "paycheck"]),
    ("Income", "Refund", ["refund", "cashback", "cash back", "rebate"]),
    ("Income", "Transfer In", ["transfer in", "zelle in", "venmo in"]),

    # Housing
    ("Housing", "Rent / Mortgage", ["rent", "mortgage", "landlord", "realty", "housing"]),
    ("Housing", "Home Insurance", ["home insurance", "homeowners insurance", "renters insurance"]),
    ("Housing", "HOA", ["hoa", "homeowners association"]),
    ("Housing", "Repairs", ["plumber", "electrician", "handyman", "home repair", "home depot", "lowe's", "lowes"]),

    # Bills & Utilities
    ("Bills & Utilities", "Electricity", ["electric", "electricity", "pge", "con ed", "comed", "duke energy"]),
    ("Bills & Utilities", "Water", ["water bill", "water utility", "sewage"]),
    ("Bills & Utilities", "Gas Utility", ["gas bill", "gas utility", "nicor", "spire", "atmos"]),
    ("Bills & Utilities", "Internet", ["comcast", "xfinity", "at&t internet", "verizon fios", "cox", "spectrum internet"]),
    ("Bills & Utilities", "Phone", ["t-mobile", "verizon wireless", "at&t wireless", "sprint", "cricket", "mint mobile"]),
    ("Bills & Utilities", "Cable / TV", ["cable", "directv", "dish network", "sling"]),
    ("Bills & Utilities", "Insurance", ["insurance", "geico", "allstate", "progressive", "state farm", "aetna", "cigna", "humana", "blue cross"]),

    # Food & Dining
    ("Food & Dining", "Groceries", [
        "grocery", "supermarket", "whole foods", "trader joe", "kroger", "safeway", "publix",
        "aldi", "walmart grocery", "target grocery", "costco", "sam's club", "heb", "wegmans",
        "sprouts", "fresh market", "market basket", "stop and shop", "food lion",
    ]),
    ("Food & Dining", "Restaurants", [
        "restaurant", "diner", "bistro", "grill", "steakhouse", "sushi", "pizza", "burger",
        "mcdonald", "wendy's", "taco bell", "chipotle", "subway", "domino", "papa john",
        "chick-fil-a", "popeyes", "kfc", "in-n-out", "shake shack", "five guys",
    ]),
    ("Food & Dining", "Coffee & Cafes", ["starbucks", "dunkin", "coffee", "cafe", "espresso", "dutch bros", "peet's"]),
    ("Food & Dining", "Food Delivery", ["doordash", "uber eats", "grubhub", "instacart", "postmates", "seamless", "delivery"]),
    ("Food & Dining", "Alcohol & Bars", ["bar", "brewery", "winery", "liquor", "beer", "wine shop", "total wine"]),

    # Transportation
    ("Transportation", "Gas & Fuel", ["shell", "chevron", "exxon", "mobil", "bp", "arco", "gas station", "fuel", "sunoco", "speedway", "circle k"]),
    ("Transportation", "Rideshare", ["uber", "lyft", "taxi", "cab"]),
    ("Transportation", "Public Transit", ["mta", "cta", "bart", "metro", "subway", "bus", "transit", "commuter rail", "amtrak"]),
    ("Transportation", "Parking", ["parking", "parkway", "garage", "meter"]),
    ("Transportation", "Car Payment", ["auto loan", "car payment", "car loan", "toyota financial", "honda financial", "ford credit"]),
    ("Transportation", "Car Insurance", ["auto insurance", "car insurance", "vehicle insurance"]),
    ("Transportation", "Car Maintenance", ["auto repair", "oil change", "tire", "mechanic", "jiffy lube", "pep boys", "midas"]),
    ("Transportation", "Tolls", ["toll", "e-zpass", "fastrak", "sunpass"]),
    ("Transportation", "Flights", ["airline", "delta", "united airlines", "american airlines", "southwest", "jetblue", "spirit airlines"]),

    # Health & Fitness
    ("Health & Fitness", "Doctor / Hospital", ["hospital", "urgent care", "clinic", "doctor", "physician", "surgery", "er visit", "emergency"]),
    ("Health & Fitness", "Pharmacy", ["pharmacy", "cvs", "walgreens", "rite aid", "duane reade", "prescription", "rx"]),
    ("Health & Fitness", "Dental & Vision", ["dentist", "dental", "orthodontist", "optometrist", "vision", "eyeglasses", "contact lens"]),
    ("Health & Fitness", "Gym & Fitness", ["gym", "fitness", "planet fitness", "la fitness", "anytime fitness", "crossfit", "peloton", "yoga", "pilates", "equinox"]),
    ("Health & Fitness", "Mental Health", ["therapy", "therapist", "psychiatrist", "counseling", "betterhelp", "talkspace"]),

    # Entertainment
    ("Entertainment", "Streaming", ["netflix", "hulu", "disney+", "disney plus", "hbo max", "peacock", "paramount+", "apple tv", "amazon prime video", "crunchyroll"]),
    ("Entertainment", "Music", ["spotify", "apple music", "tidal", "pandora", "youtube music", "soundcloud"]),
    ("Entertainment", "Gaming", ["playstation", "xbox", "nintendo", "steam", "epic games", "apple arcade", "google play games"]),
    ("Entertainment", "Movies & Events", ["cinema", "amc theatres", "regal", "fandango", "ticketmaster", "stubhub", "concert", "event"]),
    ("Entertainment", "Books & Media", ["audible", "kindle", "scribd", "book", "library fine"]),
    ("Entertainment", "Hobbies", ["hobby", "craft", "art supply", "michaels", "joann"]),

    # Shopping
    ("Shopping", "Online Shopping", ["amazon", "ebay", "etsy", "shopify", "wish.com", "online order"]),
    ("Shopping", "Clothing & Apparel", ["zara", "h&m", "gap", "old navy", "banana republic", "nordstrom", "macy's", "tj maxx", "marshall", "ross", "clothing", "apparel", "fashion"]),
    ("Shopping", "Electronics", ["apple store", "best buy", "newegg", "micro center", "b&h photo", "electronics"]),
    ("Shopping", "General Retail", ["target", "walmart", "costco", "sam's club", "dollar general", "dollar tree", "five below", "big lots"]),
    ("Shopping", "Home & Garden", ["ikea", "wayfair", "bed bath", "williams sonoma", "pottery barn", "west elm", "crate and barrel", "home goods"]),

    # Personal Care
    ("Personal Care", "Haircut & Salon", ["salon", "barber", "hair", "haircut", "hairstyle", "great clips", "supercuts"]),
    ("Personal Care", "Beauty & Spa", ["spa", "massage", "nail", "manicure", "pedicure", "sephora", "ulta", "beauty", "skincare"]),
    ("Personal Care", "Laundry", ["laundry", "dry clean", "laundromat"]),

    # Education
    ("Education", "Tuition & Fees", ["tuition", "university", "college", "school fee", "enrollment"]),
    ("Education", "Online Courses", ["udemy", "coursera", "skillshare", "masterclass", "linkedin learning", "pluralsight", "codecademy"]),
    ("Education", "Books & Supplies", ["textbook", "school supply", "staples", "office depot"]),
    ("Education", "Childcare", ["daycare", "babysitter", "nursery", "preschool", "after school"]),

    # Travel
    ("Travel", "Hotels & Lodging", ["hotel", "marriott", "hilton", "hyatt", "airbnb", "vrbo", "motel", "inn", "resort"]),
    ("Travel", "Car Rental", ["hertz", "enterprise rent", "avis", "budget car", "car rental"]),
    ("Travel", "Vacation", ["travel", "trip", "vacation", "expedia", "booking.com", "tripadvisor", "kayak"]),

    # Savings & Investments
    ("Savings & Investments", "Savings Transfer", ["savings transfer", "transfer to savings", "savings deposit"]),
    ("Savings & Investments", "Investments", ["robinhood", "fidelity", "schwab", "vanguard", "etrade", "td ameritrade", "betterment", "wealthfront", "investment", "brokerage"]),
    ("Savings & Investments", "Retirement", ["401k", "ira", "roth ira", "retirement"]),
    ("Savings & Investments", "Crypto", ["coinbase", "crypto", "bitcoin", "ethereum", "binance"]),
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
