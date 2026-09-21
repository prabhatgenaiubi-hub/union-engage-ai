import smtplib
from email.message import EmailMessage
from email.utils import formataddr
import httpx
from app.core.config import settings

def send_transactional_email(to_email:str,to_name:str,subject:str,text_content:str)->str:
    if settings.smtp_username and settings.smtp_password:
        message=EmailMessage();message["From"]=formataddr((settings.smtp_from_name,settings.smtp_from_email));message["To"]=formataddr((to_name,to_email));message["Subject"]=subject;message.set_content(text_content)
        try:
            with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=settings.brevo_timeout_seconds) as client:
                client.ehlo();client.starttls();client.ehlo();client.login(settings.smtp_username,settings.smtp_password);client.send_message(message)
        except (smtplib.SMTPException,OSError) as exc:raise RuntimeError(f"Brevo SMTP failed: {exc}") from exc
        return message["Message-ID"] or f"smtp-{to_email}"
    if not settings.brevo_api_key or not settings.smtp_from_email:
        raise RuntimeError("Brevo email is not configured")
    response=httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key":settings.brevo_api_key,"accept":"application/json","content-type":"application/json"},
        json={"sender":{"name":settings.smtp_from_name,"email":settings.smtp_from_email},"to":[{"email":to_email,"name":to_name}],"subject":subject,"textContent":text_content,"tags":["union-engage-opportunity"]},
        timeout=settings.brevo_timeout_seconds,
    )
    try:response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail=response.json().get("message","Brevo rejected the email") if response.headers.get("content-type","").startswith("application/json") else "Brevo rejected the email"
        raise RuntimeError(detail) from exc
    message_id=response.json().get("messageId")
    if not message_id:raise RuntimeError("Brevo did not return a message ID")
    return message_id
