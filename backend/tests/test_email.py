def test_smtp_email_has_delivery_headers_and_message_id(monkeypatch):
    from app.services import email as service

    captured = []
    class SMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): pass
        def starttls(self): pass
        def login(self, *args): pass
        def send_message(self, message):
            captured.append(message)
            return {}

    monkeypatch.setattr(service.smtplib, "SMTP", SMTP)
    monkeypatch.setattr(service.settings, "resend_api_key", "")
    monkeypatch.setattr(service.settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(service.settings, "smtp_password", "smtp-password")
    monkeypatch.setattr(service.settings, "smtp_from_email", "verified@example.com")
    message_id = service.send_transactional_email("customer@example.com", "Customer", "Subject", "Approved content")
    assert message_id == captured[0]["Message-ID"]
    assert captured[0]["Date"] and captured[0]["Reply-To"] == "verified@example.com"
    assert captured[0]["To"] == "Customer <customer@example.com>"


def test_resend_is_preferred_and_returns_provider_message_id(monkeypatch):
    from app.services import email as service

    captured = {}

    class Response:
        headers = {"content-type": "application/json"}

        def raise_for_status(self): pass

        def json(self): return {"id": "resend-message-id"}

    def post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(service.httpx, "post", post)
    monkeypatch.setattr(service.settings, "resend_api_key", "resend-key")
    monkeypatch.setattr(service.settings, "resend_from_email", "onboarding@resend.dev")
    monkeypatch.setattr(service.settings, "resend_from_name", "UNION-ENGAGE-AI")
    monkeypatch.setattr(service.settings, "smtp_from_email", "reply@example.com")

    message_id = service.send_transactional_email("customer@example.com", "Customer", "Subject", "Approved content")

    assert message_id == "resend-message-id"
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["authorization"] == "Bearer resend-key"
    assert captured["json"]["from"] == "UNION-ENGAGE-AI <onboarding@resend.dev>"
    assert captured["json"]["to"] == ["customer@example.com"]
    assert captured["json"]["reply_to"] == "reply@example.com"


def test_smtp_email_embeds_generated_image(monkeypatch):
    from app.services import email as service

    captured=[]
    class SMTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def ehlo(self):pass
        def starttls(self):pass
        def login(self,*args):pass
        def send_message(self,message):captured.append(message);return {}

    monkeypatch.setattr(service.smtplib,"SMTP",SMTP)
    monkeypatch.setattr(service.settings,"resend_api_key","")
    monkeypatch.setattr(service.settings,"smtp_username","smtp-user")
    monkeypatch.setattr(service.settings,"smtp_password","smtp-password")
    monkeypatch.setattr(service.settings,"smtp_from_email","verified@example.com")
    service.send_transactional_email("customer@example.com","Customer","Subject","Approved content",b"png-bytes","offer.png")
    attachments=list(captured[0].iter_attachments())
    assert attachments[0].get_filename()=="offer.png"
    assert attachments[0].get_content_type()=="image/png"
    assert "cid:campaign-image" in str(captured[0])

def test_custom_image_marker_controls_html_position():
    from app.services.email import _html_content
    html=_html_content("Hello Customer,\n\nBefore image\n\n[CAMPAIGN_IMAGE]\n\nAfter image","campaign-image","custom")
    assert html.index("Before image")<html.index("cid:campaign-image")<html.index("After image")
    assert "[CAMPAIGN_IMAGE]" not in html

def test_image_size_and_alignment_are_rendered():
    from app.services.email import _html_content
    html=_html_content("Hello", "campaign-image", "top", 55, 240, "right")
    assert "width:55%" in html
    assert "height:240px" in html
    assert "text-align:right" in html
    assert "margin:0 0 0 auto" in html
