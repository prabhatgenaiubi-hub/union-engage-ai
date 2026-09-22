import re
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

UNKNOWN = "I couldn't find a clear answer in the approved public knowledge. Please ask a more specific question or contact the bank."

PUBLIC_CAPABILITIES = "I can answer general questions about Union Bank accounts, debit cards, deposits, loans, digital banking, and service policies. You can ask about a specific product or process. For your balance, transactions, card status, or a service request, please sign in."


def is_general_question(question: str) -> bool:
    text = " ".join(question.lower().split()).strip(" ?!.,")
    return bool(
        re.fullmatch(r"(?:what|which) (?:help|helps|services?|assistance|support) (?:can |do |does |will )?you (?:provide|offer|give)", text)
        or re.fullmatch(r"(?:what|which) (?:can|do) you (?:help (?:me )?with|do)", text)
        or re.fullmatch(r"(?:who|what) are you|what is your (?:name|purpose)|how can you help(?: me)?", text)
    )


def general_answer(question: str) -> str | None:
    """Answer questions about the assistant itself without claiming bank policy facts."""
    prompt = (
        "You are an AI chat assistant on the Union Bank login page. The visitor is asking what help YOU, the chat assistant, provide. "
        "Answer as the chat assistant, not as the bank. Start with 'I can help'. Answer naturally in one or two short sentences. "
        "You can answer general questions about bank accounts, cards, deposits, loans, digital banking, and service policies. "
        "Say 'bank accounts', never 'your accounts'. "
        "For personal account or service status, visitors must sign in. Do not claim to perform transactions or access accounts. "
        "Do not describe the bank's staff, products, or technology as services you personally provide. "
        "Do not invent specific bank rates, fees, eligibility, timelines, or policies. Never request a PIN, OTP, CVV, password, or full card number.\n"
        f"Visitor question: {question[:300]}\nAnswer:"
    )
    try:
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2, "num_predict": 100}},
            timeout=min(settings.ollama_timeout_seconds, 25),
        )
        response.raise_for_status()
        answer = response.json()["response"].strip()
        if not answer or len(answer) > 450 or "INSUFFICIENT" in answer.upper() or not answer.lower().startswith("i can help") or re.search(r"\b(?:pin|otp|cvv|password|account number)\b|\byour\s+(?:\w+\s+){0,2}accounts?\b", answer, re.I):
            return None
        return answer
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        logger.warning("Public general response unavailable: %s", exc)
        return None

def supports_question_focus(question: str, passage: str) -> bool:
    """Require evidence for details that are easy for a model to invent."""
    q = question.lower()
    source = passage.lower()
    if re.search(r"\b(?:documents?|papers?|proofs?)\b", q) and not re.search(r"\b(?:documents?|papers?|proofs?|kyc)\b", source):
        return False
    if re.search(r"\b(?:how long|how many days|when will|timeframe|timeline)\b", q) and not re.search(r"\b(?:days?|weeks?|months?|hours?|timeframe|timeline|within)\b", source):
        return False
    return True

def generated_answer(question: str, passage: str, history: list | None = None) -> str | None:
    """Use a local model only after an approved passage has been selected."""
    cleaned = re.sub(r"(?im)^\s*(?:classification:.*|page\s+\d+\s+of\s+\d+|.*central office.*)\s*$", "", passage).strip()
    prompt = "You are the public Union Bank login-page assistant. Answer the current question directly in plain language using only the approved excerpt below. Summarize the actual answer in complete sentences, under 110 words. Never repeat the question or its opening phrase. Never use ellipses. Do not copy document headers, classification markings, or long passages. If the excerpt does not answer the question, reply exactly INSUFFICIENT. Do not invent rates, timeframes, eligibility, or account details. Never ask for PIN, OTP, CVV, password, or full card number.\nApproved excerpt:\n" + cleaned[:4500] + "\nCurrent question: " + question + "\nConcise answer:"
    try:
        response = httpx.post(f"{settings.ollama_base_url.rstrip('/')}/api/generate", json={"model": settings.ollama_model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 180}}, timeout=min(settings.ollama_timeout_seconds, 45))
        response.raise_for_status()
        answer = response.json()["response"].strip()
        if not answer or "INSUFFICIENT" in answer.upper() or len(answer) > 900 or "..." in answer or "…" in answer:
            return None
        return answer
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        logger.warning("Public assistant generation unavailable: %s", exc)
        return None

def broad_help(query: str) -> str | None:
    text = " ".join(query.lower().split()).strip(" ?!.,")
    if re.fullmatch(r"(?:what|which) (?:banking )?services (?:do |can )?you (?:provide|offer|help with)|what (?:can|do) you (?:help (?:me )?with|do)|how can you help(?: me)?|tell me (?:about )?(?:your|the) services", text):
        return "I can answer general questions about Union Bank accounts, debit cards, deposits, loans, digital banking, and service policies. You can ask about a specific product or process. For your balance, transactions, card status, or a service request, please sign in."
    if re.fullmatch(r"(?:can|could|would) you (?:please )?(?:provide |give me |offer )?help (?:me )?with (?:my |a )?(?:debit|atm) card", text) or re.fullmatch(r"(?:i need|help me with|help with) (?:my |a )?(?:debit|atm) card", text):
        return "Yes, I can help with general debit card questions. Is your card lost, blocked, not working, or do you want to know how to request or use one? Please don't share your PIN, CVV, OTP, or full card number here."
    return None

def policy_answer(query: str, passage: str, current_question: str | None = None) -> str | None:
    text = query.lower()
    current = (current_question or query).lower()
    source = re.sub(r"\s+", " ", passage.lower())
    if re.search(r"\b(?:customer|consumer)s?\b", text) and re.search(r"\brights\b", text) and all(item in source for item in ("right to fair treatment", "right to transparency", "right to suitability", "right to privacy", "right to grievance redressal")):
        return "The Customer Rights Policy lists the right to fair treatment; transparent, fair and honest dealing; suitable products and services; privacy; and grievance redressal and compensation. It also describes banking facilities for senior citizens and people with disabilities."
    if "atm" in text and ("failed" in text or "cash not dispensed" in text) and "amount wrongfully debited" in source and "5 days" in source and "rs.100/- per day" in source:
        if "eligible" in current:
            return "If your account was debited but the ATM did not dispense cash, the wrongly debited amount should be reversed within T+5 days. The policy provides ₹100 per day for any delay beyond T+5. Whether compensation is due in your case depends on the transaction and reversal dates; please sign in for an account-specific check."
        if "how much" in current or "what will be the amount" in current or "re-imburse" in current:
            return "The bank should reverse the full amount wrongly debited. If that reversal takes longer than T+5 days from the failed ATM transaction, the policy adds ₹100 for each day of delay. Your exact total depends on the amount debited and when it was reversed."
        return "For a failed ATM transaction where the account was debited but cash was not dispensed, the bank should reverse the full wrongful debit within T+5 days. If it is delayed beyond T+5, the policy provides ₹100 per day of delay. Please sign in to check a specific transaction."
    if "lost in transit" in text and "compensat" in text and all(part in source for part in ("interest will be paid", "15 days", "duplicate cheque")):
        return "If notice of the lost instrument comes after the applicable collection period, the bank pays interest for the excess period at the policy rate. It also pays savings account interest for a further 15 days to allow for obtaining and collecting a duplicate instrument, and reimburses reasonable duplicate instrument charges when a receipt is provided."
    return None

def pdf_answer(query: str, matches: list[dict]) -> tuple[str, dict] | None:
    terms = set(re.findall(r"[a-z]{3,}", query.lower())) - {"what", "when", "where", "which", "who", "how", "can", "could", "would", "please", "tell", "about", "bank", "union", "the", "and", "for", "with", "are", "does", "this", "that", "help", "provide"}
    if not terms:
        return None
    candidates = []
    for match in matches:
        clean = re.sub(r"\s+", " ", match["content"]).strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", clean):
            sentence = re.sub(r"^(?:[a-z]\.|\d+[.)]|[ivx]+[.)])\s*", "", sentence, flags=re.I).strip()
            words = set(re.findall(r"[a-z]{3,}", sentence.lower()))
            overlap = len(words & terms)
            if overlap and 35 <= len(sentence) <= 300 and not re.search(r"classifi|internal|page\s*\||maker tower", sentence, re.I):
                candidates.append((overlap, sentence, match))
    if not candidates:
        return None
    _, sentence, match = max(candidates, key=lambda item: (item[0], -len(item[1])))
    if len(terms) > 1 and len(set(re.findall(r"[a-z]{3,}", sentence.lower())) & terms) < 2:
        return None
    return sentence, match
