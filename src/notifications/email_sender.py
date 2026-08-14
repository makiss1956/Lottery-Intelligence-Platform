"""Email notification sender for lottery predictions."""
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger("EmailSender")

class LotteryEmailSender:
    def __init__(self):
        self.cfg = get_config()
        self.enabled = self.cfg.get("notifications", "email", "enabled", default=False)
        self.smtp_server = self.cfg.get("notifications", "email", "smtp_server", default="smtp.gmail.com")
        self.smtp_port = int(self.cfg.get("notifications", "email", "smtp_port", default=587))
        self.username = os.getenv("LOTTERY_EMAIL_USER", "")
        self.password = os.getenv("LOTTERY_EMAIL_PASS", "")
        self.to_email = os.getenv("LOTTERY_EMAIL_TO", self.username)

    def send_prediction(self, prediction: Dict[str, Any], stats: Dict[str, Any]) -> bool:
        if not self.enabled or not self.username or not self.password:
            logger.info("Email notifications disabled or credentials missing.")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🎯 Eurojackpot Prediction — {prediction['prediction_for_date']}"
            msg["From"] = self.username
            msg["To"] = self.to_email

            primary = prediction.get("primary_candidates", [])
            euro = prediction.get("euro_candidates", [])
            conf = prediction.get("confidence", {})

            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>🔮 Eurojackpot Prediction</h2>
                <p><b>Next Draw:</b> {prediction.get('prediction_for_date', 'N/A')}</p>
                <hr>
                <h3>Primary Candidates (7 numbers, ranked by probability):</h3>
                <ol>
                    {''.join(f'<li><b>{n}</b> (score: {conf.get("primary", {}).get(n, "N/A")})</li>' for n in primary)}
                </ol>
                <h3>Euro Candidates (3 numbers, ranked):</h3>
                <ol>
                    {''.join(f'<li><b>{n}</b> (score: {conf.get("euro", {}).get(n, "N/A")})</li>' for n in euro)}
                </ol>
                <hr>
                <p><b>Method:</b> {prediction.get('method', 'N/A')}</p>
                <p><b>Total draws in DB:</b> {stats.get('total_draws', 'N/A')}</p>
                <p style="color: #666; font-size: 12px;">
                    Disclaimer: For educational purposes only.
                </p>
            </body>
            </html>
            """

            msg.attach(MIMEText(html, "html"))

            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.sendmail(self.username, self.to_email, msg.as_string())

            logger.info("Prediction email sent to %s", self.to_email)
            return True

        except Exception as e:
            logger.error("Failed to send email: %s", e)
            return False
