import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)

class EmailSender:
    def __init__(self):
        cfg = get_config()
        self.smtp_server = os.getenv("SMTP_SERVER") or cfg.get("email.smtp_server") or "smtp.gmail.com"
        
        # Ασφαλής μετατροπή θύρας SMTP με fallback στο 587
        raw_port = os.getenv("SMTP_PORT") or cfg.get("email.smtp_port")
        if raw_port is None or raw_port == "":
            self.port = 587
        else:
            try:
                self.port = int(raw_port)
            except ValueError:
                self.port = 587

        self.sender_email = os.getenv("SMTP_USER") or cfg.get("email.sender_email")
        self.password = os.getenv("SMTP_PASSWORD")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL") or cfg.get("email.recipient_email")

    def send_email(self, subject: str, body: str) -> bool:
        if not self.sender_email or not self.password or not self.recipient_email:
            logger.warning("Email credentials missing. Skipping email notification.")
            return False
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()
                server.login(self.sender_email, self.password)
                server.send_message(msg)

            logger.info("Email notification sent successfully.")
            return True
        except Exception as e:
            logger.error("Failed to send email: %s", e)
            return False
