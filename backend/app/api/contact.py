"""Public contact intake with persistence, abuse controls and optional SMTP."""
import logging
import smtplib
import threading
import time
from collections import defaultdict, deque
from email.message import EmailMessage

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ContactMessage
from app.db.session import get_db

router = APIRouter(prefix="/contact", tags=["contact"])
logger = logging.getLogger(__name__)
_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=10, max_length=10000)
    website: str = Field(default="", max_length=500)


def deliver(name: str, email: str, message: str, message_id: int) -> None:
    settings = get_settings()
    if not all((settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.smtp_from, settings.contact_email)):
        logger.info("Contact message stored", extra={"message_id": message_id})
        return
    mail = EmailMessage()
    mail["From"] = settings.smtp_from
    mail["To"] = settings.contact_email
    mail["Reply-To"] = email
    mail["Subject"] = "Lumen contact message"
    mail.set_content(f"From: {name}\n\n{message}")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(mail)
    except (OSError, smtplib.SMTPException):
        logger.error("Contact SMTP delivery failed; message remains stored", extra={"message_id": message_id})


@router.get("")
def contact_info() -> dict[str, str | None]:
    return {"email": get_settings().contact_email or None}


@router.post("", status_code=201)
def submit_contact(body: ContactRequest, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict[str, str]:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        attempts = _attempts[ip]
        while attempts and now - attempts[0] >= 3600:
            attempts.popleft()
        if len(attempts) >= 5:
            raise HTTPException(status_code=429, detail="Too many messages. Please try again later.")
        attempts.append(now)
    if body.website:
        return {"status": "received"}
    if not body.name.strip() or not body.message.strip():
        raise HTTPException(status_code=422, detail="Name and message cannot be blank.")
    message = ContactMessage(name=body.name.strip(), email=str(body.email), message=body.message.strip())
    db.add(message)
    db.commit()
    db.refresh(message)
    tasks.add_task(deliver, message.name, message.email, message.message, message.id)
    return {"status": "received"}
