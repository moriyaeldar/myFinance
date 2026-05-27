from sqlalchemy import create_engine, Column, String, Float, Date, Boolean, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./myfinance.db")
# Render provides postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    account_id = Column(String, index=True)
    date = Column(Date, index=True)
    description = Column(String)
    merchant_name = Column(String, nullable=True)
    amount = Column(Float)           # positive = expense, negative = income
    category = Column(String)        # auto-detected category
    category_group = Column(String)  # high-level group
    source = Column(String)          # "plaid" | "csv" | "demo"
    currency = Column(String, default="USD")
    pending = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)            # checking, credit, savings
    subtype = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    plaid_access_token = Column(String, nullable=True)
    source = Column(String)          # "plaid" | "csv" | "demo"
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CategorySettings(Base):
    __tablename__ = "category_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_group = Column(String, unique=True)
    status = Column(String, default="essential")  # "essential" | "optional" | "cut"
    monthly_budget = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Seed default category settings
    db = SessionLocal()
    try:
        defaults = [
            ("Income",              "essential"),
            ("Housing",             "essential"),
            ("Food & Dining",       "essential"),
            ("Restaurants & Cafes", "optional"),
            ("Communication",       "essential"),
            ("Bills & Utilities",   "essential"),
            ("Insurance",           "essential"),
            ("Transportation",      "essential"),
            ("Health & Fitness",    "essential"),
            ("Children & Family",   "essential"),
            ("Clothing & Fashion",  "optional"),
            ("Home & Garden",       "optional"),
            ("Shopping",            "optional"),
            ("Entertainment",       "optional"),
            ("Personal Care",       "optional"),
            ("Pets",                "optional"),
            ("Gifts & Donations",   "optional"),
            ("Education",           "essential"),
            ("Travel",              "optional"),
            ("Loans & Credit",      "essential"),
            ("ATM & Cash",          "optional"),
            ("Savings & Investments","essential"),
            ("Other",               "optional"),
        ]
        for group, status in defaults:
            exists = db.query(CategorySettings).filter_by(category_group=group).first()
            if not exists:
                db.add(CategorySettings(category_group=group, status=status))
        db.commit()
    finally:
        db.close()
