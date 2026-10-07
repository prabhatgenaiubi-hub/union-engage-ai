import smtplib
import base64
from html import escape
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
import httpx
from app.core.config import settings

IMAGE_MARKER="[CAMPAIGN_IMAGE]"
def _html_content(text_content:str,image_cid:str|None=None,image_position:str="top",image_width_percent:int=100,image_height_px:int=300,image_alignment:str="center")->str:
    width=max(25,min(100,image_width_percent))
    height=max(100,min(600,image_height_px))
    alignment=image_alignment if image_alignment in {"left","center","right"} else "center"
    margin={"left":"0 auto 0 0","center":"0 auto","right":"0 0 0 auto"}[alignment]
    image=f'<p style="text-align:{alignment}"><img src="cid:{image_cid}" alt="Personalized campaign visual" width="{width}%" style="display:block;width:{width}%;max-width:100%;height:{height}px;object-fit:cover;margin:{margin};border:0" /></p>' if image_cid else ""
    parts=[part for part in text_content.split("\n") if part.strip()]
    paragraphs=[];placed=False
    for part in parts:
        if image and IMAGE_MARKER in part:
            before,after=part.split(IMAGE_MARKER,1)
            if before.strip():paragraphs.append(f"<p>{escape(before.strip())}</p>")
            paragraphs.append(image);placed=True
            if after.strip():paragraphs.append(f"<p>{escape(after.strip())}</p>")
        else:paragraphs.append(f"<p>{escape(part)}</p>")
    if image and not placed:
        index=1 if image_position=="after_greeting" and paragraphs else len(paragraphs) if image_position=="bottom" else 0
        paragraphs.insert(index,image)
    return f"<html><body>{''.join(paragraphs)}</body></html>"

def send_transactional_email(to_email:str,to_name:str,subject:str,text_content:str,image_content:bytes|None=None,image_filename:str="campaign.png",image_position:str="top",image_width_percent:int=100,image_height_px:int=300,image_alignment:str="center")->str:
    image_cid="campaign-image" if image_content else None
    plain_text=text_content.replace(IMAGE_MARKER,"").strip()
    if settings.resend_api_key:
        payload={"from":formataddr((settings.resend_from_name,settings.resend_from_email)),"to":[to_email],"subject":subject,"text":plain_text,"html":_html_content(text_content,image_cid,image_position,image_width_percent,image_height_px,image_alignment)}
        if image_content:payload["attachments"]=[{"filename":image_filename,"content":base64.b64encode(image_content).decode("ascii"),"content_id":image_cid}]
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
        message=EmailMessage();message["From"]=formataddr((settings.smtp_from_name,settings.smtp_from_email));message["To"]=formataddr((to_name,to_email));message["Subject"]=subject;message["Date"]=formatdate(localtime=True);message["Message-ID"]=make_msgid(domain=sender_domain);message["Reply-To"]=settings.smtp_from_email;message.set_content(plain_text);message.add_alternative(_html_content(text_content,image_cid,image_position,image_width_percent,image_height_px,image_alignment),subtype="html")
        if image_content:message.get_payload()[1].add_related(image_content,maintype="image",subtype="png",cid=f"<{image_cid}>",filename=image_filename)
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
        json={"sender":{"name":settings.smtp_from_name,"email":settings.smtp_from_email},"to":[{"email":to_email,"name":to_name}],"subject":subject,"textContent":plain_text,"htmlContent":_html_content(text_content),"tags":["union-engage-opportunity"],**({"attachment":[{"name":image_filename,"content":base64.b64encode(image_content).decode("ascii")}]} if image_content else {})},
        timeout=settings.brevo_timeout_seconds,
    )
    try:response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail=response.json().get("message","Brevo rejected the email") if response.headers.get("content-type","").startswith("application/json") else "Brevo rejected the email"
        raise RuntimeError(detail) from exc
    message_id=response.json().get("messageId")
    if not message_id:raise RuntimeError("Brevo did not return a message ID")
    return message_id
