"""Extract structured, reviewable details from a public lead conversation."""
import re

MONEY = re.compile(
    r"(?:(?:₹|rs\.?|inr)\s*)?(\d[\d,]*(?:\.\d+)?)\s*"
    r"(crores?|cr|lakhs?|lacs?|thousands?|k)?\s*(rupees?)?",
    re.I,
)


def _money_value(match: re.Match) -> int:
    value = float(match.group(1).replace(",", ""))
    unit = (match.group(2) or "").lower()
    if unit.startswith(("crore", "cr")):
        value *= 10_000_000
    elif unit.startswith(("lakh", "lac")):
        value *= 100_000
    elif unit.startswith(("thousand", "k")):
        value *= 1_000
    return round(value)


def extract_lead_details(messages: list[str], product: str, pending_question: str = "") -> tuple[int | None, str, dict]:
    """Return requested amount, clean enquiry, and other facts explicitly shared."""
    clean_pending = pending_question.split("\nProduct of interest:", 1)[0].strip()
    enquiry = clean_pending or next((item.strip() for item in reversed(messages) if product.lower() in item.lower()), "")
    requested: list[tuple[int, int, str, str]] = []
    income: list[tuple[int, str]] = []
    timeline = ""
    requirement_message = enquiry

    for index, message in enumerate(messages):
        lower = message.lower()
        timeline_match = re.search(r"\b(?:within|in the next|next|by)\s+\d+\s+(?:days?|weeks?|months?|years?)\b|\b(?:immediately|urgent(?:ly)?|this year)\b", message, re.I)
        if timeline_match:
            timeline = timeline_match.group(0)
        for match in MONEY.finditer(message):
            # A unit or currency marker is required so phone numbers and dates
            # cannot become financial requirements.
            marked = bool(match.group(2) or match.group(3) or re.match(r"(?:₹|rs\.?|inr)", match.group(0), re.I))
            if not marked:
                continue
            value = _money_value(match)
            context = lower[max(0, match.start() - 55):min(len(lower), match.end() + 55)]
            if re.search(r"\b(?:salary|income|earn|earning|take home)\b", context):
                income.append((value, match.group(0).strip()))
                continue
            score = 2 if re.search(r"\b(?:loan|need|require|want|amount|finance|budget|borrow)\b", context) else 1
            requested.append((score, index, match.group(0).strip(), message.strip()))

    details: dict = {}
    amount = None
    if requested:
        _, _, amount_text, requirement_message = max(requested, key=lambda item: (item[0], item[1]))
        amount = next(_money_value(match) for match in MONEY.finditer(requirement_message) if match.group(0).strip() == amount_text)
        details["amount_as_shared"] = amount_text
    if income:
        details["stated_income"] = income[-1][0]
        details["income_as_shared"] = income[-1][1]
    if timeline:
        details["timeline_as_shared"] = timeline
    if requirement_message:
        details["requirement_message"] = requirement_message[:500]
    return amount, enquiry[:500], details
