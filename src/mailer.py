import smtplib
from email.message import EmailMessage
from src import config


def _smtp_send(msg: EmailMessage) -> None:
    user = config.get_secret("GMAIL_USER")
    pw = config.get_secret("GMAIL_APP_PASSWORD")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)


def send(html: str, subject: str, recipients: list) -> bool:
    if not recipients:
        return False
    msg = EmailMessage()
    msg["From"] = config.get_secret("GMAIL_USER")
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("HTML 메일입니다. HTML 지원 클라이언트로 보세요.")
    msg.add_alternative(html, subtype="html")
    for attempt in range(2):
        try:
            _smtp_send(msg)
            return True
        except Exception:
            if attempt == 1:
                return False
    return False
