import math
import re

from app.models import FinancialGoal

FIELDS = ["monthly_income", "monthly_expenses", "target_amount", "timeline_months"]
QUESTIONS = {
    "monthly_income": "What is your approximate monthly take-home income?",
    "monthly_expenses": "What are your average essential and regular monthly expenses?",
    "target_amount": "What is the total amount you want to save for this goal?",
    "timeline_months": "By when would you like to reach it (in months or years)?",
}
AMOUNT = r"(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(crores?|lakhs?|lacs?|thousands?|k)?"

def _money(raw: str, unit: str | None) -> float:
    value = float(raw.replace(",", "")); unit = (unit or "").lower()
    if unit.startswith("crore"): return value * 10_000_000
    if unit.startswith(("lakh", "lac")): return value * 100_000
    if unit.startswith("thousand") or unit == "k": return value * 1_000
    return value

def _keyword_amount(text: str, keywords: list[str]) -> float | None:
    words = "|".join(re.escape(word) for word in keywords)
    after = re.search(rf"(?:{words})[^0-9₹]{{0,35}}{AMOUNT}", text, re.I)
    before = re.search(rf"{AMOUNT}[^a-z]{{0,16}}(?:{words})", text, re.I)
    match = after or before
    return _money(match.group(1), match.group(2)) if match else None

def _timeline(text: str) -> int | None:
    match = re.search(r"\b([0-9]+)\s*(months?|mos?|years?|yrs?)\b", text, re.I)
    if match: return int(match.group(1)) * (12 if match.group(2).lower().startswith(("year", "yr")) else 1)
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
    match = re.search(r"\b(one|two|three|four|five)\s+(months?|years?)\b", text, re.I)
    if match:
        value = words[match.group(1).lower()]
        return value * (12 if match.group(2).lower().startswith("year") else 1)
    return None

def _goal_name(text: str, current: str) -> str:
    names = {
        "Emergency Fund": ["emergency fund", "rainy day"], "Education Goal": ["education", "college", "school", "study"],
        "Wedding Goal": ["wedding", "marriage"], "Travel Goal": ["travel", "holiday", "vacation", "trip"],
        "Retirement Goal": ["retirement", "retire"], "Business Goal": ["business", "startup"],
        "Car Goal": ["car", "vehicle"], "Home Goal": ["house", "home", "property"],
    }
    lowered = text.lower()
    for name, terms in names.items():
        if any(term in lowered for term in terms): return name
    return current or "Savings Goal"

def coach(goal: FinancialGoal, text: str) -> dict:
    data = dict(dict(goal.coaching_plan or {}).get("inputs", {}))
    income = _keyword_amount(text, ["take home", "take-home", "salary", "income", "earn"])
    expenses = _keyword_amount(text, ["monthly expenses", "expenses", "expense", "spending", "spend"])
    saved = _keyword_amount(text, ["already saved", "have saved", "currently saved", "current savings"])
    target = _keyword_amount(text, ["goal of", "target", "need", "cost", "want to save", "save"])
    timeline = _timeline(text)
    if income is not None: data["monthly_income"] = income
    if expenses is not None: data["monthly_expenses"] = expenses
    if target is not None and saved is None: data["target_amount"] = target
    if saved is not None: data["saved_amount"] = saved
    if timeline is not None: data["timeline_months"] = timeline
    missing = next((field for field in FIELDS if not data.get(field)), None)
    detected = any(value is not None for value in (income, expenses, target, saved, timeline))
    if missing and not detected:
        bare = re.fullmatch(rf"\s*{AMOUNT}\s*(?:per month|monthly)?\s*", text, re.I)
        if bare:
            data[missing] = _money(bare.group(1), bare.group(2))
            missing = next((field for field in FIELDS if not data.get(field)), None)
    goal.name = _goal_name(text, goal.name)
    goal.monthly_income = float(data.get("monthly_income", 0)); goal.monthly_expenses = float(data.get("monthly_expenses", 0))
    goal.target_amount = float(data.get("target_amount", 0)); goal.saved_amount = float(data.get("saved_amount", goal.saved_amount or 0))
    goal.timeline_months = int(data.get("timeline_months", 0)); remaining = max(0, goal.target_amount - goal.saved_amount)
    goal.monthly_required = remaining / goal.timeline_months if goal.timeline_months else 0
    plan = {"inputs": data}
    if not missing:
        surplus = goal.monthly_income - goal.monthly_expenses; safe_capacity = max(0, surplus * 0.8)
        feasible = goal.monthly_required <= safe_capacity and surplus > 0
        suggested = goal.timeline_months if feasible or remaining == 0 else math.ceil(remaining / safe_capacity) if safe_capacity else None
        guidance = []
        if surplus <= 0: guidance.append("First close the monthly income-expense gap before committing money to this goal")
        elif feasible: guidance.append(f"Automate ₹{goal.monthly_required:,.0f} toward the goal soon after income is received")
        else:
            guidance.append(f"A sustainable starting contribution is about ₹{safe_capacity:,.0f} per month")
            guidance.append(f"Consider extending the timeline to about {suggested} months or reducing the target")
        guidance.extend([f"Build or protect an emergency buffer of about ₹{goal.monthly_expenses * 3:,.0f}", "Review discretionary spending and goal progress once each month"])
        plan.update({"remaining_amount": round(remaining, 2), "monthly_surplus": round(surplus, 2),
            "savings_rate_percent": round((surplus / goal.monthly_income * 100) if goal.monthly_income else 0, 1),
            "monthly_goal_required": round(goal.monthly_required, 2),
            "recommended_monthly_contribution": round(goal.monthly_required if feasible else safe_capacity, 2),
            "emergency_fund_target": round(goal.monthly_expenses * 3, 2), "feasible": feasible,
            "suggested_timeline_months": suggested, "guidance": guidance})
        goal.status = "Active"
    else: goal.status = "Planning"
    goal.coaching_plan = plan
    return {"complete": not missing, "next_field": missing, "next_question": QUESTIONS.get(missing), "plan": plan, "name": goal.name, "status": goal.status}
