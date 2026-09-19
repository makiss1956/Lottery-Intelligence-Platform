```python
"""Email notification sender."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from src.core.config import get_config
from src.core.logger import get_logger


logger = get_logger("EmailSender")


class LotteryEmailSender:

    def __init__(self):

        self.cfg = get_config()

        self.enabled = self.cfg.get(
            "notifications",
            "email",
            "enabled",
            default=False,
        )

        self.smtp_server = self.cfg.get(
            "notifications",
            "email",
            "smtp_server",
            default="smtp.gmail.com",
        )

        self.smtp_port = int(
            self.cfg.get(
                "notifications",
                "email",
                "smtp_port",
                default=587,
            )
        )

        self.username = os.getenv(
            "LOTTERY_EMAIL_USER",
            "",
        )

        self.password = os.getenv(
            "LOTTERY_EMAIL_PASS",
            "",
        )

        self.to_email = os.getenv(
            "LOTTERY_EMAIL_TO",
            self.username,
        )

    def send_prediction(
        self,
        prediction: Dict[str, Any],
        stats: Dict[str, Any] | None = None,
    ) -> bool:

        stats = stats or {}

        if (
            not self.enabled
            or not self.username
            or not self.password
        ):

            logger.warning(
                "Email disabled or credentials missing."
            )

            return False

        target_date = prediction.get(
            "for_draw_date",
            prediction.get(
                "prediction_for_date",
                "N/A",
            ),
        )

        primary = prediction.get(
            "primary_candidates",
            [],
        )

        joker = prediction.get(
            "joker_candidates",
            prediction.get(
                "euro_candidates",
                [],
            ),
        )

        evaluation = prediction.get(
            "evaluation"
        )

        if not joker:

            joker_text = "N/A"

        else:

            joker_text = str(joker[0])

        # -----------------------------------------------------
        # Previous prediction evaluation
        # -----------------------------------------------------

        evaluation_html = ""

        if evaluation:

            matched_main = evaluation.get(
                "matched_main_numbers",
                [],
            )

            matched_joker = evaluation.get(
                "matched_euro_numbers",
                [],
            )

            evaluation_html = f"""
            <hr>

            <h3>Έλεγχος προηγούμενης πρόβλεψης</h3>

            <p>
                <b>Κλήρωση:</b>
                {evaluation.get("draw_date", "N/A")}
            </p>

            <p>
                <b>Κύριοι αριθμοί:</b>
                {evaluation.get("main_hits_count", 0)} / 3
            </p>

            <p>
                <b>Joker:</b>
                {evaluation.get("euro_hits_count", 0)} / 1
            </p>

            <p>
                <b>Κοινοί κύριοι αριθμοί:</b>
                {matched_main}
            </p>

            <p>
                <b>Κοινός Joker:</b>
                {matched_joker}
            </p>
            """

        # -----------------------------------------------------
        # Email
        # -----------------------------------------------------

        msg = MIMEMultipart("alternative")

        msg["Subject"] = (
            "Eurojackpot 3+1 Prediction - "
            f"{target_date}"
        )

        msg["From"] = self.username
        msg["To"] = self.to_email

        primary_html = "".join(
            f"<li><b>{number}</b></li>"
            for number in primary
        )

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">

        <h2>Eurojackpot Statistical Prediction</h2>

        <p>
            <b>Next draw:</b> {target_date}
        </p>

        <hr>

        <h3>3 Main Numbers</h3>

        <ol>
            {primary_html}
        </ol>

        <h3>Joker / Euro Number</h3>

        <p style="font-size: 24px;">
            <b>{joker_text}</b>
        </p>

        {evaluation_html}

        <hr>

        <p>
            <b>Method:</b>
            {prediction.get("method", "N/A")}
        </p>

        <p>
            <b>Total draws:</b>
            {stats.get("total_draws", "N/A")}
        </p>

        <p style="font-size: 11px; color: #666;">
            Statistical/educational analysis only.
            Lottery outcomes are random and past results
            do not guarantee future results.
        </p>

        </body>
        </html>
        """

        msg.attach(
            MIMEText(
                html,
                "html",
                "utf-8",
            )
        )

        try:

            context = ssl.create_default_context()

            with smtplib.SMTP(
                self.smtp_server,
                self.smtp_port,
                timeout=30,
            ) as server:

                server.ehlo()

                server.starttls(
                    context=context
                )

                server.ehlo()

                server.login(
                    self.username,
                    self.password,
                )

                server.sendmail(
                    self.username,
                    self.to_email,
                    msg.as_string(),
                )

            logger.info(
                "Prediction email sent to %s",
                self.to_email,
            )

            return True

        except Exception:

            logger.exception(
                "Prediction email failed."
            )

            return False
```
