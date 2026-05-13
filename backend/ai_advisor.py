"""
Claude-powered financial advisor.
Analyzes spending data and returns structured recommendations.
"""
import os
import json
from typing import List, Dict

import anthropic


def _build_spending_summary(categories: List[dict], monthly_trends: List[dict], stats: dict) -> str:
    """Convert raw data into a compact text summary for the prompt."""
    lines = []

    lines.append("=== FINANCIAL SUMMARY ===")
    lines.append(f"Monthly income (avg): ${stats.get('total_income_mtd', 0):,.2f}")
    lines.append(f"Monthly expenses (MTD): ${stats.get('total_expenses_mtd', 0):,.2f}")
    lines.append(f"Net this month: ${stats.get('net_mtd', 0):,.2f}")
    lines.append("")

    lines.append("=== SPENDING BY CATEGORY (all-time) ===")
    for cat in sorted(categories, key=lambda x: x["total"], reverse=True):
        status = cat.get("status", "optional")
        budget = f" | budget: ${cat['monthly_budget']:,.0f}/mo" if cat.get("monthly_budget") else ""
        merchants = ", ".join(cat["top_merchants"][:3]) if cat.get("top_merchants") else "N/A"
        lines.append(
            f"  {cat['category_group']}: ${cat['monthly_avg']:,.2f}/mo avg "
            f"({cat['percentage_of_total']:.1f}% of spending) | "
            f"status: {status}{budget} | top: {merchants}"
        )

    if monthly_trends:
        lines.append("")
        lines.append("=== MONTHLY TRENDS (recent) ===")
        for m in monthly_trends[-4:]:
            lines.append(
                f"  {m['month']}: income=${m['income']:,.2f}, expenses=${m['expenses']:,.2f}, net=${m['net']:,.2f}"
            )

    return "\n".join(lines)


SYSTEM_PROMPT = """You are an expert personal finance analyst. You analyze household spending data and provide
actionable, specific recommendations. Be direct, quantitative, and prioritize recommendations by impact.

You must respond ONLY with valid JSON in this exact structure:
{
  "recommendations": [
    {
      "title": "Short title (max 60 chars)",
      "description": "2-3 sentence explanation with specific numbers from the data",
      "estimated_monthly_savings": 0.00,
      "priority": "high|medium|low",
      "category": "The category group name",
      "action": "One specific actionable step the user can take today"
    }
  ],
  "summary": "2-3 sentence overall financial health summary with key insight",
  "savings_potential_monthly": 0.00,
  "savings_potential_annual": 0.00,
  "health_score": 75,
  "health_label": "Good|Fair|Needs Attention|Excellent"
}

Rules:
- Provide 5-8 recommendations ordered from highest to lowest impact
- health_score is 0-100 based on savings rate, debt, and discretionary spending
- Be specific: mention actual merchant names and dollar amounts from the data
- estimated_monthly_savings must be realistic (not wishful thinking)
- Focus on actionable changes, not generic advice
- If income > 0, comment on savings rate (income - expenses) / income
- Flag subscriptions that stack up (Netflix + Disney+ + HBO = overlap)"""


def get_ai_recommendations(
    categories: List[dict],
    monthly_trends: List[dict],
    stats: dict,
    cut_categories: List[str] = None,
) -> dict:
    """
    Call Claude to analyze spending and return structured recommendations.
    Falls back to a rule-based analysis if the API key is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    spending_summary = _build_spending_summary(categories, monthly_trends, stats)

    if cut_categories:
        spending_summary += f"\n\n=== USER MARKED AS 'CUT' ===\n{', '.join(cut_categories)}"

    user_message = f"Please analyze this household financial data and provide recommendations:\n\n{spending_summary}"

    if not api_key:
        return _rule_based_fallback(categories, stats)

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)


def _rule_based_fallback(categories: List[dict], stats: dict) -> dict:
    """Simple rule-based recommendations when no API key is available."""
    recommendations = []
    total_savings_potential = 0.0

    # Check streaming subscriptions
    entertainment = next((c for c in categories if c["category_group"] == "Entertainment"), None)
    if entertainment and entertainment["monthly_avg"] > 50:
        savings = min(entertainment["monthly_avg"] * 0.4, 30)
        total_savings_potential += savings
        recommendations.append({
            "title": "Review Streaming Subscriptions",
            "description": (
                f"You spend ~${entertainment['monthly_avg']:.0f}/mo on entertainment. "
                "Multiple streaming services often overlap in content. "
                "Audit which ones you actually use weekly."
            ),
            "estimated_monthly_savings": round(savings, 2),
            "priority": "medium",
            "category": "Entertainment",
            "action": "List all subscriptions and cancel any you haven't used in the past 2 weeks.",
        })

    # Check food delivery
    food = next((c for c in categories if c["category_group"] == "Food & Dining"), None)
    if food and food["monthly_avg"] > 400:
        savings = food["monthly_avg"] * 0.25
        total_savings_potential += savings
        recommendations.append({
            "title": "Reduce Food Delivery & Dining Out",
            "description": (
                f"Food & Dining is costing ~${food['monthly_avg']:.0f}/mo — "
                f"{food['percentage_of_total']:.0f}% of your total spending. "
                "Cooking at home more frequently can cut this significantly."
            ),
            "estimated_monthly_savings": round(savings, 2),
            "priority": "high",
            "category": "Food & Dining",
            "action": "Meal-prep Sunday meals for the week to reduce weekday delivery orders.",
        })

    # Check shopping
    shopping = next((c for c in categories if c["category_group"] == "Shopping"), None)
    if shopping and shopping["monthly_avg"] > 200:
        savings = shopping["monthly_avg"] * 0.3
        total_savings_potential += savings
        recommendations.append({
            "title": "Set a Monthly Shopping Budget",
            "description": (
                f"Shopping averages ${shopping['monthly_avg']:.0f}/mo. "
                "Unplanned purchases add up quickly. "
                "A defined budget creates a natural limit."
            ),
            "estimated_monthly_savings": round(savings, 2),
            "priority": "medium",
            "category": "Shopping",
            "action": f"Set a hard shopping budget of ${shopping['monthly_avg']*0.7:.0f}/mo and track it weekly.",
        })

    # Savings rate check
    income = stats.get("total_income_mtd", 0)
    expenses = stats.get("total_expenses_mtd", 0)
    if income > 0:
        savings_rate = (income - expenses) / income * 100
        if savings_rate < 20:
            recommendations.append({
                "title": "Boost Your Savings Rate",
                "description": (
                    f"Your current savings rate is ~{savings_rate:.0f}% "
                    f"(${income - expenses:.0f}/mo). "
                    "Financial experts recommend saving 20% of income. "
                    f"Target: ${income * 0.20:.0f}/mo."
                ),
                "estimated_monthly_savings": round(income * 0.20 - (income - expenses), 2),
                "priority": "high",
                "category": "Savings & Investments",
                "action": "Set up an automatic transfer to savings on payday before spending.",
            })

    health_score = 75
    if income > 0:
        rate = (income - expenses) / income
        if rate >= 0.3:
            health_score = 95
            label = "Excellent"
        elif rate >= 0.2:
            health_score = 80
            label = "Good"
        elif rate >= 0.1:
            health_score = 60
            label = "Fair"
        else:
            health_score = 40
            label = "Needs Attention"
    else:
        label = "Fair"

    return {
        "recommendations": recommendations,
        "summary": (
            f"Your monthly expenses of ${expenses:,.0f} against income of ${income:,.0f} "
            f"leave a net of ${income - expenses:,.0f}. "
            "Focus on the high-priority recommendations above to improve your financial health."
        ),
        "savings_potential_monthly": round(total_savings_potential, 2),
        "savings_potential_annual": round(total_savings_potential * 12, 2),
        "health_score": health_score,
        "health_label": label,
    }
