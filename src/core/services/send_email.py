import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, EmailStr

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "emails"
env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")


class SendEmailRequestDTO(BaseModel):

    to: EmailStr

    sender: EmailStr | None = None

    subject: str

    template_name: str

    html_substitutions: dict | None = None


def send_email(request_dto: SendEmailRequestDTO):

    # SMTP CREDENTIALS COME FROM THE ENVIRONMENT, FAIL CLEARLY IF THEY ARE MISSING

    if not SMTP_USER or not SMTP_PASS:

        raise RuntimeError("SMTP_USER and SMTP_PASS environment variables must be set")

    # GET TEMPLATE

    html_template = env.get_template(request_dto.template_name)

    # ALWAYS RENDER THE TEMPLATE

    html_template = html_template.render(**(request_dto.html_substitutions or {}))

    # BUILD MESSAGE

    sender = request_dto.sender if request_dto.sender else SMTP_USER

    msg = MIMEMultipart("alternative")

    msg["Subject"] = request_dto.subject

    msg["From"] = sender

    msg["To"] = request_dto.to

    msg.attach(MIMEText(html_template, "html", "utf-8"))

    # SEND EMAIL

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:

        server.starttls()

        server.login(SMTP_USER, SMTP_PASS)

        server.sendmail(sender, request_dto.to, msg.as_string())
