"""Email notification dispatcher."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger("EmailSender")

class EmailSender:
    def __init__(self):
        cfg = get_config()
        self.enabled = cfg.get("email.enabled", True)
        self.host = os.getenv("SMTP_HOST") or cfg.get("email.smtp_host")
        self.port = int(os.getenv("SMTP_PORT") or cfg.get("email.smtp_port", 587))
        self.user = os.getenv("SMTP_USER") or cfg.get("email.smtp_user")
        self.password = os.getenv("SMTP_PASS") or cfg.get("email.smtp_pass")
        self.email_from = os.getenv("EMAIL_FROM") or cfg.get("email.email_from") or self.user
        self.email_to = os.getenv("EMAIL_TO") or cfg.get("email.email_to")

        if not all([self.host, self.user, self.password, self.email_to]):
            logger.warning("Email not fully configured. Notifications disabled.")
            self.enabled = False

    def send_prediction_report(self, 
                               draw_data: Dict[str, Any], 
                               prediction_data: Dict[str, Any],
                               evaluation: Dict[str, Any] = None,
                               stats: Dict[str, Any] = None,
                               history: List[Dict[str, Any]] = None) -> None:
        if not self.enabled:
            logger.info("Email disabled or misconfigured. Skipping.")
            return

        subject = f"🎯 Eurojackpot Report — New Draw {draw_data.get('draw_date', 'N/A')}"
        html = self._build_html(draw_data, prediction_data, evaluation, stats, history)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.email_from, self.email_to.split(","), msg.as_string())
            logger.info("Email sent successfully to %s", self.email_to)
        except Exception as e:
            logger.error("Failed to send email: %s", e)
            raise

    def _build_html(self, draw, prediction, evaluation, stats, history):
        rows = []
        rows.append("<html><head><style>")
        rows.append("body{font-family:Arial,sans-serif; background:#f5f5f5; padding:20px;}")
        rows.append(".container{max-width:700px; margin:auto; background:#fff; padding:20px; border-radius:8px;}")
        rows.append(".box{background:#f0f8ff; border-left:4px solid #007bff; padding:12px; margin:10px 0;}")
        rows.append(".success{background:#d4edda; border-left-color:#28a745;}")
        rows.append(".warning{background:#fff3cd; border-left-color:#ffc107;}")
        rows.append("table{width:100%; border-collapse:collapse; margin-top:10px;}")
        rows.append("th,td{border:1px solid #ddd; padding:8px; text-align:center;}")
        rows.append("th{background:#007bff; color:#fff;}")
        rows.append(".num{display:inline-block; width:32px; height:32px; line-height:32px; border-radius:50%; background:#007bff; color:#fff; margin:2px; font-weight:bold;}")
        rows.append(".euro{background:#ffc107; color:#000;}")
        rows.append("</style></head><body><div class='container'>")
        rows.append("<h2>🎯 Lottery Intelligence Platform</h2>")
        rows.append("<p style='color:#666;'>Automated report generated after latest draw.</p>")

        # New Draw
        rows.append("<div class='box'>")
        rows.append(f"<h3>📥 Latest Draw — {draw.get('draw_date','')}</h3>")
        rows.append("<p><strong>Primary:</strong> " + " ".join(f"<span class='num'>{n}</span>" for n in draw.get("primary_numbers",[])) + "</p>")
        rows.append("<p><strong>Euro:</strong> " + " ".join(f"<span class='num euro'>{n}</span>" for n in draw.get("euro_numbers",[])) + "</p>")
        if draw.get("jackpot_euros"):
            rows.append(f"<p><strong>Jackpot:</strong> €{draw['jackpot_euros']:,.2f}</p>")
        rows.append("</div>")

        # Evaluation of previous prediction
        if evaluation:
            cls = "success" if evaluation.get("main_hits",0) >= 3 else "warning"
            rows.append(f"<div class='box {cls}'>")
            rows.append("<h3>📊 Previous Prediction Evaluation</h3>")
            rows.append(f"<p>Main Hits: <strong>{evaluation.get('main_hits',0)}/5</strong> &nbsp;|&nbsp; Euro Hits: <strong>{evaluation.get('euro_hits',0)}/2</strong></p>")
            rows.append(f"<p>Score: <strong>{evaluation.get('score_percentage',0)}%</strong></p>")
            if evaluation.get("matched_main"):
                rows.append("<p>Matched Primary: " + ", ".join(map(str, evaluation["matched_main"])) + "</p>")
            if evaluation.get("matched_euro"):
                rows.append("<p>Matched Euro: " + ", ".join(map(str, evaluation["matched_euro"])) + "</p>")
            rows.append("</div>")

        # New Prediction
        rows.append("<div class='box'>")
        rows.append(f"<h3>🔮 Next Prediction (Method: {prediction.get('method','N/A')})</h3>")
        rows.append("<p><strong>Primary Candidates (7):</strong> " + " ".join(f"<span class='num'>{n}</span>" for n in prediction.get("primary_candidates",[])) + "</p>")
        rows.append("<p><strong>Euro Candidates (3):</strong> " + " ".join(f"<span class='num euro'>{n}</span>" for n in prediction.get("euro_candidates",[])) + "</p>")
        rows.append("</div>")

        # Stats
        if stats:
            rows.append("<div class='box'>")
            rows.append("<h3>📈 Quick Stats (All History)</h3>")
            rows.append(f"<p>Total Draws in DB: <strong>{stats.get('total_draws',0)}</strong></p>")
            rows.append(f"<p>Hot Primary: {stats.get('hot_primary',[])}</p>")
            rows.append(f"<p>Cold Primary: {stats.get('cold_primary',[])}</p>")
            rows.append(f"<p>Most Overdue Primary: {stats.get('most_overdue_primary',[])}</p>")
            rows.append("</div>")

        # Prediction History Table
        if history:
            rows.append("<h3>📚 Prediction History (Last 10)</h3>")
            rows.append("<table><tr><th>For Date</th><th>Predicted Primary</th><th>Predicted Euro</th><th>Main Hits</th><th>Euro Hits</th><th>Score</th></tr>")
            for h in history[:10]:
                pmain = h.get("predicted_primary","") or "—"
                peuro = h.get("predicted_euro","") or "—"
                mh = h.get("main_hits")
                eh = h.get("euro_hits")
                sc = h.get("score_percentage")
                rows.append(f"<tr><td>{h.get('prediction_for_date','')}</td><td>{pmain}</td><td>{peuro}</td><td>{mh if mh is not None else '—'}</td><td>{eh if eh is not None else '—'}</td><td>{sc if sc is not None else '—'}%</td></tr>")
            rows.append("</table>")

        rows.append("<hr><p style='font-size:12px; color:#999;'>Lottery Intelligence Platform — Educational Research Only. Past statistics do not influence future random draws.</p>")
        rows.append("</div></body></html>")
        return "\n".join(rows)
