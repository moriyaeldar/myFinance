"""
Generates realistic demo transactions so the app can be explored
without connecting a real bank account.
"""
import uuid
import random
from datetime import date, timedelta
from analyzer import categorize

DEMO_ACCOUNT_ID = "demo-checking-001"
DEMO_CREDIT_ID = "demo-credit-001"

DEMO_TRANSACTIONS_TEMPLATES = [
    # (description, merchant, amount_range, frequency_per_month, account)
    ("DIRECT DEPOSIT EMPLOYER", "Employer Corp", (-5500, -5500), 1, DEMO_ACCOUNT_ID),

    # Housing
    ("RENT PAYMENT", "Main St Apartments", (2200, 2200), 1, DEMO_ACCOUNT_ID),
    ("RENTERS INSURANCE", "Allstate", (25, 25), 1, DEMO_ACCOUNT_ID),

    # Utilities
    ("ELECTRICITY BILL", "PG&E", (80, 140), 1, DEMO_ACCOUNT_ID),
    ("INTERNET BILL", "Comcast Xfinity", (75, 75), 1, DEMO_ACCOUNT_ID),
    ("PHONE BILL", "T-Mobile", (65, 65), 1, DEMO_ACCOUNT_ID),
    ("GAS UTILITY", "Nicor Gas", (30, 60), 1, DEMO_ACCOUNT_ID),

    # Food & Dining
    ("WHOLE FOODS MARKET", "Whole Foods", (80, 200), 3, DEMO_CREDIT_ID),
    ("TRADER JOE'S", "Trader Joe's", (40, 120), 2, DEMO_CREDIT_ID),
    ("STARBUCKS", "Starbucks", (5, 12), 8, DEMO_CREDIT_ID),
    ("CHIPOTLE MEXICAN GRILL", "Chipotle", (12, 18), 4, DEMO_CREDIT_ID),
    ("DOORDASH", "DoorDash", (25, 55), 5, DEMO_CREDIT_ID),
    ("LOCAL RESTAURANT", "The Italian Kitchen", (40, 90), 3, DEMO_CREDIT_ID),
    ("MCDONALD'S", "McDonald's", (8, 15), 2, DEMO_CREDIT_ID),

    # Transportation
    ("SHELL GAS STATION", "Shell", (45, 65), 3, DEMO_CREDIT_ID),
    ("UBER TRIP", "Uber", (12, 35), 6, DEMO_CREDIT_ID),
    ("PARKING GARAGE", "City Parking", (15, 40), 4, DEMO_CREDIT_ID),
    ("MTA TRANSIT", "MTA", (33, 33), 1, DEMO_ACCOUNT_ID),

    # Streaming & Entertainment
    ("NETFLIX", "Netflix", (15, 15), 1, DEMO_CREDIT_ID),
    ("SPOTIFY", "Spotify", (11, 11), 1, DEMO_CREDIT_ID),
    ("DISNEY PLUS", "Disney+", (8, 8), 1, DEMO_CREDIT_ID),
    ("HBO MAX", "HBO Max", (16, 16), 1, DEMO_CREDIT_ID),
    ("AMC THEATRES", "AMC Theatres", (15, 40), 1, DEMO_CREDIT_ID),

    # Shopping
    ("AMAZON.COM", "Amazon", (25, 200), 6, DEMO_CREDIT_ID),
    ("TARGET", "Target", (30, 120), 3, DEMO_CREDIT_ID),
    ("ZARA USA", "Zara", (60, 150), 1, DEMO_CREDIT_ID),

    # Health & Fitness
    ("PLANET FITNESS", "Planet Fitness", (25, 25), 1, DEMO_ACCOUNT_ID),
    ("CVS PHARMACY", "CVS", (15, 60), 2, DEMO_CREDIT_ID),
    ("DR SMITH CLINIC", "Dr. Smith", (40, 200), 0.5, DEMO_CREDIT_ID),

    # Personal Care
    ("GREAT CLIPS HAIRCUT", "Great Clips", (25, 35), 0.5, DEMO_CREDIT_ID),
    ("SEPHORA", "Sephora", (30, 90), 0.5, DEMO_CREDIT_ID),

    # Savings
    ("TRANSFER TO SAVINGS", "Savings Account", (-400, -400), 1, DEMO_ACCOUNT_ID),
]


def generate_demo_transactions(months: int = 6) -> list:
    today = date.today()
    transactions = []

    for i in range(months):
        month_date = today.replace(day=1) - timedelta(days=30 * i)

        for desc, merchant, amt_range, freq, account in DEMO_TRANSACTIONS_TEMPLATES:
            # Determine how many times this transaction occurs this month
            count = int(freq) + (1 if random.random() < (freq % 1) else 0)
            if freq < 1 and random.random() > freq:
                continue

            for _ in range(max(1, count)):
                day = random.randint(1, 28)
                txn_date = month_date.replace(day=day)
                if txn_date > today:
                    continue

                lo, hi = amt_range
                if lo == hi:
                    amount = float(lo)
                else:
                    amount = round(random.uniform(lo, hi), 2)

                # Add small month-to-month variation (±10%)
                if amount > 0:
                    amount = round(amount * random.uniform(0.92, 1.10), 2)

                group, category = categorize(desc, merchant)
                if amount < 0:
                    group = "Income"
                    category = "Income"

                transactions.append({
                    "id": f"demo-{uuid.uuid4().hex}",
                    "account_id": account,
                    "date": txn_date,
                    "description": desc,
                    "merchant_name": merchant,
                    "amount": amount,
                    "category": category,
                    "category_group": group,
                    "source": "demo",
                    "currency": "ILS",
                    "pending": False,
                })

    return sorted(transactions, key=lambda x: x["date"], reverse=True)


DEMO_ACCOUNTS = [
    {
        "id": DEMO_ACCOUNT_ID,
        "name": "Checking Account",
        "type": "depository",
        "subtype": "checking",
        "institution": "Demo Bank",
        "balance": 3842.50,
        "currency": "ILS",
        "plaid_access_token": None,
        "source": "demo",
    },
    {
        "id": DEMO_CREDIT_ID,
        "name": "Rewards Credit Card",
        "type": "credit",
        "subtype": "credit card",
        "institution": "Demo Bank",
        "balance": 1247.83,
        "currency": "ILS",
        "plaid_access_token": None,
        "source": "demo",
    },
]
