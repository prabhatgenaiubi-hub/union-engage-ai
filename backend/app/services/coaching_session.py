"""Persistent coaching dialogue. Amounts and scenarios are calculated locally."""
import math
import re
from datetime import datetime, timedelta
from app.services.financial_coach import AMOUNT, _money, _timeline, _keyword_amount, _goal_name

QUESTIONS = {
    "focus": "What would you most like to improve: your budget, debt, emergency savings, or a purchase goal?",
    "monthly_income": "What is your approximate monthly take-home income? If it varies, use a conservative month.",
    "monthly_expenses": "How much do you spend monthly, excluding loan or credit-card repayments?",
    "debt_payment": "What are your total monthly loan and credit-card repayments? Say zero if you have none.",
    "emergency_savings": "How much accessible emergency savings do you have, separate from money saved for this goal?",
    "income_stability": "Is your income regular or variable?",
    "dependants": "How many people depend on your income? You can skip this.",
    "debt_balance": "What is your total outstanding debt? An estimate is fine, or you can skip.",
    "debt_apr": "What is the highest annual interest rate on your debts, as a percentage? You can skip if unsure.",
    "target_amount": "What total amount would you like to have for this goal?",
    "saved_amount": "How much have you already set aside specifically for this goal?",
    "timeline_months": "When would you like to reach the goal, in months or years?",
}
MONEY_FIELDS = {"monthly_income", "monthly_expenses", "debt_payment", "emergency_savings", "debt_balance", "target_amount", "saved_amount"}

def coach(goal, text):
    previous = dict(goal.coaching_plan or {})
    data = dict(previous.get("inputs", {}))
    actions = list(previous.get("actions", []))
    reviews = list(previous.get("reviews", []))
    t = text.strip().lower()
    pending = previous.get("next_field", "focus")
    focus = next((label for label, terms in [
        ("goal", ("save for", "want to save", "car purchase", "buy a car", "buy a home", "buy a house")),
        ("debt", ("debt", "repayment", "credit card")),
        ("budget", ("budget", "overspend", "expenses", "spending")),
        ("emergency", ("emergency", "rainy day")),
        ("goal", ("save for", "want to save", "car", "home", "house", "travel", "education", "retirement", "goal"))
    ] if any(term in t for term in terms)), None)
    if "focus" not in data and focus: data["focus"] = focus
    if pending == "focus" and t and not focus and t not in ("hello", "hi"):
        data["focus"] = "budget"
        data["motivation"] = text[:500]
    # Each labelled amount is constrained to its own clause to avoid borrowing a later field's number.
    labels = {
        "monthly_income": ["take-home", "take home", "salary", "income", "earn"],
        "monthly_expenses": ["monthly expenses", "expenses", "spending"],
        "debt_payment": ["monthly repayments", "debt payment", "repayments", "emi"],
        "emergency_savings": ["emergency savings", "emergency buffer"],
        "debt_balance": ["outstanding debt", "debt balance"],
        "target_amount": ["target", "goal amount", "cost", "want to save"],
        "saved_amount": ["already saved", "have saved", "saved total", "current savings"],
    }
    changed = False
    for field, words in labels.items():
        for clause in re.split(r"[;\n]|\band\b|,(?!\d)|\.(?!\d)", t if "what if" not in t else ""):
            terms = "|".join(re.escape(word) for word in words)
            match = re.search(rf"(?:{terms})\s*(?:(?:is|are|of|about|around|approximately|rs)\s*)*{AMOUNT}", clause, re.I)
            value = _money(match.group(1),match.group(2)) if match else None
            if value is not None:
                data[field] = value
                changed = True
                break
    duration = _timeline(t)
    if duration and "what if" not in t:
        data["timeline_months"] = min(duration, 1200)
        changed = True
    if "what if" not in t and (pending == "income_stability" or "income" in t):
        if any(word in t for word in ("variable", "irregular", "freelance")): data["income_stability"] = "variable"; changed = True
        elif any(word in t for word in ("regular", "stable", "fixed")): data["income_stability"] = "regular"; changed = True
    if pending in QUESTIONS and not changed and "what if" not in t:
        if t in ("skip", "not sure", "unknown", "prefer not to say"):
            data[pending] = None
        elif pending == "income_stability" and t in ("regular", "variable"):
            data[pending] = t
        else:
            bare = re.fullmatch(rf"{AMOUNT}\s*(?:%|per month|monthly|people|dependants)?", t, re.I)
            value = _money(bare.group(1), bare.group(2)) if bare else 0 if t in ("none", "zero", "no debt", "no savings") else None
            if value is not None:
                if pending in MONEY_FIELDS: data[pending] = value
                elif pending in ("dependants", "timeline_months", "debt_apr"): data[pending] = min(value, 1200)
    if data.get("focus") == "goal":
        goal.name = _goal_name(text, goal.name)
    else:
        goal.name = {"budget": "Budget coaching", "debt": "Debt coaching", "emergency": "Emergency planning"}.get(data.get("focus"), "Financial coaching")
    fields = ["focus", "monthly_income", "monthly_expenses", "debt_payment", "emergency_savings", "income_stability", "dependants"]
    if data.get("focus") == "debt" or (data.get("debt_payment") or 0) > 0: fields += ["debt_balance", "debt_apr"]
    if data.get("focus") == "goal": fields += ["target_amount", "saved_amount", "timeline_months"]
    missing = next((key for key in fields if key not in data), None)
    income, expenses, debt = (float(data.get(key) or 0) for key in ("monthly_income", "monthly_expenses", "debt_payment"))
    surplus = income-expenses-debt
    capacity = max(0, surplus*0.8)
    months = 6 if data.get("income_stability") == "variable" else 3
    buffer = (expenses+debt)*months
    unknown = [key for key in fields if key in data and data[key] is None]
    cash_known = all(data.get(key) is not None for key in ("monthly_income","monthly_expenses","debt_payment"))
    priorities = []
    if not cash_known: priorities.append("Track income, spending and repayments for one month before setting a contribution.")
    elif surplus <= 0: priorities.append("Your commitments use all available income. Review flexible spending and discuss repayment difficulties with your lender before adding a savings commitment.")
    elif debt > 0: priorities.append("Keep required repayments current; list debt rates and balances before deciding where extra repayments should go.")
    if data.get("emergency_savings") is not None and data["emergency_savings"] < buffer:
        priorities.append("Discuss a starter emergency buffer before committing the full surplus to longer-term goals.")
    priorities.append("Choose one manageable spending change and review it in a month.")
    target = float(data.get("target_amount") or 0)
    saved = float(data.get("saved_amount") or 0)
    timeline = int(data.get("timeline_months") or 0)
    required = max(0, target-saved)/timeline if timeline else 0
    feasible = cash_known and timeline > 0 and required <= capacity
    summary = f"Monthly income ₹{income:,.0f}, spending excluding repayments ₹{expenses:,.0f}, repayments ₹{debt:,.0f}."
    summary += f" Remaining monthly cash: ₹{surplus:,.0f}." if cash_known else " Some figures are unknown; this is a provisional picture."
    options = [
        {"id": "track", "title": "Track spending for one month", "amount": None},
        {"id": "buffer", "title": "Build an emergency buffer", "amount": round(capacity, 2) if cash_known else None},
        {"id": "debt", "title": "Review debt balances and rates", "amount": None},
    ]
    if target and timeline: options.append({"id": "goal", "title": "Work toward this goal", "amount": round(min(required, capacity), 2) if cash_known else None})
    if changed:
        actions = [{**action, "status": "Needs review"} for action in actions]
    stage = "discovery" if missing else "confirmation"
    confirmed = previous.get("confirmed", False) and not changed
    if not missing and t in ("yes", "correct", "confirm", "that is correct", "yes correct"): confirmed = True
    if confirmed and not missing: stage = "planning"
    chosen = next((option for option in options if t == f"choose {option['id']}"), None)
    if chosen and confirmed:
        actions = [{"id": chosen["id"], "title": chosen["title"], "monthly_amount": chosen["amount"], "status": "Agreed",
                    "agreed_at": datetime.utcnow().isoformat(), "review_on": (datetime.utcnow()+timedelta(days=30)).date().isoformat()}]
    if actions and not missing and confirmed: stage = "review"
    if stage == "review" and t and not chosen:
        reviews = (reviews+[{"date": datetime.utcnow().isoformat(), "note": text[:1000]}])[-12:]
    if changed and previous.get("confirmed"): confirmed=False; stage="confirmation" if not missing else stage
    question = QUESTIONS[missing] if missing else "Does this financial picture look correct? Confirm it, or tell me what to change."
    if confirmed: question = "Which action feels manageable? Choose track, buffer, debt" + (", or goal." if target and timeline else ".")
    if stage == "review": question = "How did your agreed action go, and what changed in your income or spending?"
    scenarios = []
    if target and timeline and cash_known:
        scenarios = [{"timeline_months": timeline, "monthly_required": round(required,2)},
                    {"timeline_months": timeline+12, "monthly_required": round(max(0,target-saved)/(timeline+12),2)}]
    if "what if" in t and duration and target:
        scenarios.append({"timeline_months": duration,"monthly_required":round(max(0,target-saved)/duration,2)})
    plan = {"inputs":data,"stage":stage,"confirmed":confirmed,"next_field":missing,"summary":summary,
        "unknown_fields":unknown,"priorities":priorities,"options":options,"actions":actions,"reviews":reviews,
        "scenarios":scenarios,"monthly_surplus":round(surplus,2),"monthly_goal_required":round(required,2),
        "recommended_monthly_contribution":round(min(required,capacity) if target else capacity,2) if cash_known else 0,
        "emergency_fund_target":round(buffer,2),"feasible":feasible,
        "suggested_timeline_months":math.ceil(max(0,target-saved)/capacity) if capacity and target else None,
        "guidance":priorities,"assumptions":["Expenses exclude repayments.", "20% of remaining cash is left unallocated in these illustrations.",
          f"Emergency-buffer illustration uses {months} months of expenses and repayments.", "No investment returns or inflation are assumed.",
          "Other goals compete for this same surplus; do not add their contributions together."]}
    goal.monthly_income=income; goal.monthly_expenses=expenses; goal.target_amount=target; goal.saved_amount=saved
    goal.timeline_months=timeline; goal.monthly_required=required; goal.status="Active" if confirmed else "Planning"
    goal.coaching_plan=plan
    response = (summary+" "+priorities[0]+" " if not missing else "We can work through this one step at a time. ")+question
    if stage=="review": response="Your agreed action is saved. "+question
    if "what if" in t and scenarios: response="Illustrative alternatives: "+"; ".join(f"{s['timeline_months']} months needs ₹{s['monthly_required']:,.0f}/month" for s in scenarios)+". Your original goal is unchanged. "+question
    return {"complete":not missing,"next_question":question,"plan":plan,"response":response,"name":goal.name,"status":goal.status}
