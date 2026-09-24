import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
import httpx
from app.core.config import settings

def send_transactional_email(to_email:str,to_name:str,subject:str,text_content:str)->str:
    if settings.resend_api_key:
        payload={"from":formataddr((settings.resend_from_name,settings.resend_from_email)),"to":[to_email],"subject":subject,"text":text_content}
        if settings.smtp_from_email:payload["reply_to"]=settings.smtp_from_email
        response=httpx.post(
            "https://api.resend.com/emails",
            headers={"authorization":f"Bearer {settings.resend_api_key}","content-type":"application/json"},
            json=payload,
            timeout=settings.resend_timeout_seconds,
        )
        try:response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:detail=response.json().get("message","Resend rejected the email")
            except ValueError:detail="Resend rejected the email"
            raise RuntimeError(f"Resend failed: {detail}") from exc
        message_id=response.json().get("id")
        if not message_id:raise RuntimeError("Resend did not return a message ID")
        return message_id
    if not settings.smtp_from_email:
        raise RuntimeError("Sender email is not configured")
    if settings.smtp_username and settings.smtp_password:
        sender_domain=settings.smtp_from_email.rsplit("@",1)[-1]
        message=EmailMessage();message["From"]=formataddr((settings.smtp_from_name,settings.smtp_from_email));message["To"]=formataddr((to_name,to_email));message["Subject"]=subject;message["Date"]=formatdate(localtime=True);message["Message-ID"]=make_msgid(domain=sender_domain);message["Reply-To"]=settings.smtp_from_email;message.set_content(text_content)
        try:
            with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=settings.brevo_timeout_seconds) as client:
                client.ehlo();client.starttls();client.ehlo();client.login(settings.smtp_username,settings.smtp_password);refused=client.send_message(message)
                if refused:raise RuntimeError(f"Email provider refused recipient: {to_email}")
        except (smtplib.SMTPException,OSError) as exc:raise RuntimeError(f"Brevo SMTP failed: {exc}") from exc
        return message["Message-ID"]
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
