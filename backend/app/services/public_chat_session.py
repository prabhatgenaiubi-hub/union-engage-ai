"""Persistent public chat sessions and opt-in external lead capture."""

import re
import secrets
from sqlalchemy.orm import Session

from app.models import PublicConversation, PublicLead, PublicMessage
from app.services.public_assistant_agent import public_assistant_agent
from app.services.public_lead_context import contextual_product
from app.services.public_conversation import social_reply
from app.services.public_lead_details import extract_lead_details
from app.services.intelligence import provider
from app.services.chat import detected_language

PRODUCTS = {
    "Home Loan": ("home loan", "buy a house", "buying a house", "buy a home", "buying a home"),
    "Vehicle Loan": ("car loan", "vehicle loan", "buy a car", "buying a car"),
    "Personal Loan": ("personal loan",),
    "Credit Card": ("credit card",),
    "Fixed Deposit": ("fixed deposit", "term deposit", "open an fd"),
    "Savings Account": ("savings account", "open an account"),
    "Current Account": ("current account",),
    "Debit Card": ("new debit card", "apply for a debit card", "get a debit card"),
}
INTEREST = re.compile(r"\b(?:i(?:'m| am)? (?:interested|looking|planning|thinking|considering|want|need|require|would like)|i have (?:a )?(?:need|requirement)(?: of| for)?|i am in need of|apply|sign up|open|buy|purchase|looking for)\b", re.I)
PHONE = re.compile(r"^\+?[0-9][0-9\s-]{8,17}$")
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CALLBACK = re.compile(r"\b(?:call me|contact me|request (?:a )?call\s?back|(?:want|need|like) (?:a )?call\s?back)\b", re.I)
DECLINE = re.compile(r"\b(?:not interested|do not|don't|dont|no longer|not now|no thanks|no thank you|rather not|prefer not)\b", re.I)

def requests_callback(message: str) -> bool:
    return bool(CALLBACK.search(message) and not DECLINE.search(message))

def detect_product_interest(message: str) -> str | None:
    text = " ".join(message.lower().replace("’", "'").split())
    if DECLINE.search(text):
        return None
    if requests_callback(text):
        return next((product for product, phrases in PRODUCTS.items() if any(phrase in text for phrase in phrases)), "Banking enquiry")
    if not INTEREST.search(text) or re.search(r"\b(?:how|what|documents|eligibility|rate|charges|fees)\b", text):
        return None
    return next((product for product, phrases in PRODUCTS.items() if any(phrase in text for phrase in phrases)), None)


def detect_contextual_interest(db: Session, conversation: PublicConversation, message: str) -> str | None:
    if social_reply(message):
        return None
    if DECLINE.search(message) or re.fullmatch(r"(?:hi|hello|hey|thanks|thank you|skip|no|cancel)[!. ]*", message, re.I):
        return None
    rows = db.query(PublicMessage).filter_by(conversation_id=conversation.id).order_by(PublicMessage.id.desc()).limit(10).all()
    # The current message has already been inserted. Exclude it and contact values.
    contact_values = {conversation.contact_name, conversation.contact_phone, conversation.contact_email}
    history = [{"role": item.role, "content": item.content[:400]} for item in reversed(rows[1:])
               if item.content not in contact_values and not re.search(r"@|\b\+?\d[\d\s-]{8,}\b", item.content)]
    return contextual_product(message, history, list(PRODUCTS) + ["Banking enquiry"]) or detect_product_interest(message)

def _reply(conversation: PublicConversation, message: str, grounded: bool = False, sources: list | None = None) -> dict:
    return {"message": message, "grounded": grounded, "sources": sources or [], "session_id": conversation.session_token, "contact_step": conversation.contact_step}

def _answer(db: Session, conversation: PublicConversation, question: str) -> dict:
    product = detect_product_interest(question)
    if product:
        return {"message": f"I can help with general {product.lower()} information. Would you like to know about eligibility, documents, or the application process?", "grounded": False, "sources": []}
    rows = db.query(PublicMessage).filter_by(conversation_id=conversation.id).order_by(PublicMessage.id.desc()).limit(10).all()
    contact_values = {conversation.contact_name, conversation.contact_phone, conversation.contact_email}
    history = [type("Turn", (), {"role": item.role, "content": item.content}) for item in reversed(rows[1:]) if item.content not in contact_values]
    return public_assistant_agent.respond(db, question, history)


def _upsert_lead(db: Session, conversation: PublicConversation) -> PublicLead | None:
    """Save a lead as soon as at least one usable contact channel is shared."""
    if not (conversation.contact_phone or conversation.contact_email):
        return None
    lead = db.query(PublicLead).filter_by(conversation_id=conversation.id).first()
    product = conversation.pending_product or (lead.product if lead else "Banking enquiry")
    question = conversation.pending_question
    contact_values = {conversation.contact_name, conversation.contact_phone, conversation.contact_email}
    user_messages = [item.content for item in conversation.messages if item.role == "user" and item.content not in contact_values]
    requested_amount, enquiry, details = extract_lead_details(user_messages, product, question)
    if lead is None:
        lead = PublicLead(conversation_id=conversation.id, product=product, name="", phone="", email="")
    lead.product = product
    lead.name = conversation.contact_name or lead.name
    lead.phone = conversation.contact_phone or lead.phone
    lead.email = conversation.contact_email or lead.email
    lead.requested_amount = requested_amount or lead.requested_amount
    lead.enquiry = enquiry or lead.enquiry
    lead.details = {**(lead.details or {}), **details}
    lead.status = "New" if lead.name and lead.phone and lead.email else "Contact details incomplete"
    db.add(lead)
    db.flush()
    return lead


def _next_contact_step(conversation: PublicConversation, received: str) -> str:
    orders = {
        "name": (("phone", conversation.contact_phone), ("email", conversation.contact_email)),
        "phone": (("email", conversation.contact_email), ("name", conversation.contact_name)),
        "email": (("phone", conversation.contact_phone), ("name", conversation.contact_name)),
    }
    return next((field for field, value in orders[received] if not value), "")


def _contact_prompt(step: str) -> str:
    prompts = {
        "name": "What name should the bank representative use?",
        "phone": "What phone number can the bank use to contact you?",
        "email": "What email address can the bank use to contact you?",
    }
    return f"{prompts[step]} You can type Skip to save the details already shared and continue."


def _finish_contact_capture(db: Session, conversation: PublicConversation, prefix: str) -> dict:
    question = conversation.pending_question
    _upsert_lead(db, conversation)
    conversation.contact_step = ""
    conversation.pending_product = ""
    conversation.pending_question = ""
    result = _answer(db, conversation, question)
    result["message"] = prefix + result["message"]
    return result

def public_chat(db: Session, message: str, session_id: str | None = None, language_code: str = "auto") -> dict:
    response_language=detected_language(message) if language_code=="auto" else language_code
    conversation = db.query(PublicConversation).filter_by(session_token=session_id).first() if session_id else None
    if conversation is None:
        conversation = PublicConversation(session_token=secrets.token_urlsafe(32), title=message[:160])
        db.add(conversation)
        db.flush()
    db.add(PublicMessage(conversation_id=conversation.id, role="user", content=message))
    db.flush()

    text = provider.to_english(message.strip(),response_language)
    continuing_interest = detect_contextual_interest(db, conversation, text) if conversation.contact_step and INTEREST.search(text) and not re.search(r"@|\b\d{8,}\b", text) else None
    is_question = bool("?" in text or re.match(r"^(?:what|how|why|when|where|which|can you|could you|tell me|explain)\b", text, re.I))
    if conversation.contact_step and (text.lower().strip(".! ") in {"skip", "no", "cancel"} or DECLINE.search(text) or is_question):
        question = conversation.pending_question
        saved = _upsert_lead(db, conversation)
        conversation.contact_declined = True
        conversation.contact_step = ""
        conversation.pending_product = ""
        conversation.pending_question = ""
        if saved is None:
            conversation.contact_name = ""
            conversation.contact_phone = ""
            conversation.contact_email = ""
        result = _answer(db, conversation, text if is_question else question)
        result["message"] = ("Thank you. The contact details you shared have been saved. " if saved else "No problem. ") + result["message"]
    elif conversation.contact_step and social_reply(text):
        result = {"message": social_reply(text), "grounded": False, "sources": []}
    elif conversation.contact_step and continuing_interest:
        # Additional loan requirements are conversation, not a visitor's name.
        conversation.pending_product = continuing_interest
        conversation.pending_question = f"{text}\nProduct of interest: {continuing_interest}"
        label = {"name": "name", "phone": "phone number", "email": "email address"}[conversation.contact_step]
        result = {"message": f"Understood, you are interested in a {conversation.pending_product.lower()}. For an optional bank follow-up, please share your {label}, or type Skip to continue with general questions.", "grounded": False, "sources": []}
    elif conversation.contact_step and EMAIL.fullmatch(text) and len(text) <= 120:
        conversation.contact_email = text
        _upsert_lead(db, conversation)
        next_step = _next_contact_step(conversation, "email")
        if next_step:
            conversation.contact_step = next_step
            result = {"message": "Thank you. " + _contact_prompt(next_step), "grounded": False, "sources": []}
        else:
            result = _finish_contact_capture(db, conversation, "Thank you. Your details have been saved for a bank representative to review. ")
    elif conversation.contact_step and PHONE.fullmatch(text) and 10 <= len(re.sub(r"\D", "", text)) <= 15:
        conversation.contact_phone = text
        _upsert_lead(db, conversation)
        next_step = _next_contact_step(conversation, "phone")
        if next_step:
            conversation.contact_step = next_step
            result = {"message": "Thank you. " + _contact_prompt(next_step), "grounded": False, "sources": []}
        else:
            result = _finish_contact_capture(db, conversation, "Thank you. Your details have been saved for a bank representative to review. ")
    elif conversation.contact_step == "name":
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,98}", text):
            result = {"message": "Please enter your name, or type Skip to continue without sharing contact details.", "grounded": False, "sources": []}
        else:
            conversation.contact_name = text
            next_step = _next_contact_step(conversation, "name")
            if next_step:
                conversation.contact_step = next_step
                result = {"message": "Thank you. " + _contact_prompt(next_step), "grounded": False, "sources": []}
            else:
                result = _finish_contact_capture(db, conversation, "Thank you. Your details have been saved for a bank representative to review. ")
    elif conversation.contact_step == "phone":
        result = {"message": "Please enter a valid phone number with 10 to 15 digits, or type Skip to save the details already shared.", "grounded": False, "sources": []}
    elif conversation.contact_step == "email":
        result = {"message": "Please enter a valid email address, or type Skip to save the details already shared.", "grounded": False, "sources": []}
    else:
        existing_lead = db.query(PublicLead).filter_by(conversation_id=conversation.id).first()
        interest = detect_contextual_interest(db, conversation, message) if existing_lead is None and (not conversation.contact_declined or requests_callback(message)) else None
        if interest:
            conversation.pending_product = interest
            conversation.pending_question = f"{message}\nProduct of interest: {interest}"
            conversation.contact_step = "name"
            conversation.contact_declined = False
            result = {"message": f"I can help with {interest.lower()}. If you would like a bank representative to follow up, you can share your name, phone number, and email. This is optional. Please enter your name first, or type Skip or ask a question to continue chatting.", "grounded": False, "sources": []}
        else:
            result = _answer(db, conversation, message)

    result["message"]=provider.from_english(result["message"],response_language)
    db.add(PublicMessage(conversation_id=conversation.id, role="assistant", content=result["message"], sources=result["sources"]))
    db.commit()
    return _reply(conversation, result["message"], result["grounded"], result["sources"])
