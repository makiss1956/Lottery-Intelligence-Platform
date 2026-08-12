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
        # Match env vars passed by GitHub Actions workflow
        self.smtp_server = os.getenv("SMTP_HOST") or cfg.get("notifications", "email", "smtp_server", default="smtp.gmail.com")

        raw_port = os.getenv("SMTP_PORT") or cfg.get("notifications", "email", "smtp_port")
        try:
            self.port = int(raw_port) if raw_port else 587
        except (ValueError, TypeError):
            self.port = 587

        self.sender_email = os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER") or cfg.get("notifications", "email", "sender_email")
        self.password = os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD")
        self.recipient_email = os.getenv("EMAIL_TO") or os.getenv("RECIPIENT_EMAIL") or cfg.get("notifications", "email", "recipient_email")

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

    def send_prediction_report(self, draw_data, prediction_data, evaluation=None, stats=None, history=None):
        """Build and send a comprehensive prediction report email."""
        subject = f"Eurojackpot Report — Draw {draw_data.get('draw_date', 'N/A')}"

        lines = []
        lines.append("=" * 60)
        lines.append("  LOTTERY INTELLIGENCE PLATFORM — REPORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"📅 Latest Draw: {draw_data.get('draw_date')}")
        lines.append(f"   Primary: {draw_data.get('primary_numbers')}")
        lines.append(f"   Euro:    {draw_data.get('euro_numbers')}")
        lines.append("")

        if evaluation:
            lines.append("📊 PREVIOUS PREDICTION EVALUATION")
            lines.append("-" * 40)
            lines.append(f"   Predicted for: {evaluation.get('prediction_for_date')}")
            lines.append(f"   Predicted Primary: {evaluation.get('predicted_primary')}")
            lines.append(f"   Actual Primary:    {evaluation.get('actual_primary')}")
            lines.append(f"   Main Hits: {evaluation.get('main_hits')}/5")
            lines.append(f"   Euro Hits: {evaluation.get('euro_hits')}/2")
            lines.append(f"   Score: {evaluation.get('score_percentage')}%")
            lines.append("")

        lines.append("🔮 NEW PREDICTION")
        lines.append("-" * 40)
        lines.append(f"   For next draw: {prediction_data.get('next_draw_date', 'N/A')}")
        lines.append(f"   Primary Candidates: {prediction_data.get('primary_candidates')}")
        lines.append(f"   Euro Candidates:    {prediction_data.get('euro_candidates')}")
        lines.append("")

        if history:
            lines.append("📚 RECENT PREDICTION HISTORY (Prediction vs Actual)")
            lines.append("-" * 80)
            lines.append(f"{'Date':<12} {'Predicted':<25} {'Actual':<25} {'Hits':<8} {'Score':<8}")
            lines.append("-" * 80)
            for h in history[:10]:
                pred = h.get("predicted_primary", "—")
                actual = h.get("actual_primary", "—")
                hits = f"{h.get('main_hits','—')}/5 + {h.get('euro_hits','—')}/2"
                score = f"{h.get('score_percentage','—')}%"
                lines.append(f"{h.get('prediction_for_date',''):<12} {pred:<25} {actual:<25} {hits:<8} {score:<8}")
            lines.append("-" * 80)

        lines.append("")
        lines.append("Disclaimer: For educational & research purposes only.")
        lines.append("=" * 60)

        body = "\n".join(lines)
        return self.send_email(subject, body)
