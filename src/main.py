"""
Main Execution Pipeline for Lottery Intelligence Platform.
Pipeline:
1. Synchronize CSV history with database.
2. Detect whether a new draw was added (via CSV or scraper fallback).
3. Validate the prediction assigned to that draw.
4. Generate exactly one prediction for the next draw.
5. Send exactly one email for the new prediction.
6. Generate dashboard.
"""
import sys
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.logger import get_logger
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EurojackpotImporter
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.analytics.predictor import ProbabilityPredictor

logger = get_logger("Main")


def send_prediction_email(prediction_data, stats):
    """Αποστολή email με την πρόβλεψη — διαβάζει ρυθμίσεις από μεταβλητές περιβάλλοντος."""
    email_user = os.getenv("LOTTERY_EMAIL_USER")
    email_to = os.getenv("LOTTERY_EMAIL_TO")
    email_pass = os.getenv("LOTTERY_EMAIL_PASS")

    if not all([email_user, email_to, email_pass]):
        logger.warning("⚠️ Λείπουν οι ρυθμίσεις email — το μήνυμα δεν θα σταλεί.")
        return False

    # Δημιουργία μηνύματος
    msg = MIMEMultipart("alternative")
    msg["From"] = email_user
    msg["To"] = email_to
    msg["Subject"] = f"🎯 Πρόβλεψη Eurojackpot — {prediction_data['prediction_for_date']}"

    # Σώμα μηνύματος
    body = f"""
Αυτόματο μήνυμα από το Lottery Intelligence Platform
======================================================

📅 Πρόβλεψη για κλήρωση: {prediction_data['prediction_for_date']}

🔢 Προτεινόμενοι αριθμοί (7 κύριοι):
{', '.join(map(str, prediction_data['primary_candidates']))}

💶 Προτεινόμενοι αριθμοί Euro (3):
{', '.join(map(str, prediction_data['euro_candidates']))}

📊 Μέθοδος: {prediction_data.get('method', 'composite_freq_delay')}

📈 Στατιστικά:
- Σύνολο κληρώσεων: {stats['total_draws']}
- Τελευταία κλήρωση: {stats['latest_draw']['draw_date']}

"""

    # Προσθήκη αποτελεσμάτων προηγούμενης πρόβλεψης αν υπάρχουν
    val = stats.get("validation")
    if val:
        body += f"""
✅ Έλεγχος προηγούμενης πρόβλεψης:
  Σωστοί κύριοι: {val.get('main_hits_count', 0)}/5
  Σωστοί Euro:   {val.get('euro_hits_count', 0)}/2
  Βαθμολογία:     {val.get('score_percentage', 0):.2f}%
"""

    body += "\n——— Το μήνυμα δημιουργήθηκε αυτόματα ———"

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        # Αποστολή μέσω SMTP (Gmail — άλλαξε αν χρησιμοποιείς άλλη υπηρεσία)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        logger.info(f"📧 Email απεστάλη με επιτυχία προς: {email_to}")
        return True
    except Exception as e:
        logger.error(f"❌ Αποτυχία αποστολής email: {str(e)}")
        return False


def run_pipeline() -> None:
    """Execute the complete lottery intelligence pipeline."""
    logger.info(
        "=================================================="
    )
    logger.info(
        "STARTING LOTTERY INTELLIGENCE PIPELINE"
    )
    logger.info(
        "=================================================="
    )

    db = DBManager()
    importer = EurojackpotImporter(db_manager=db)

    # -------------------------------------------------
    # STEP 1 — Συγχρονισμός δεδομένων
    # -------------------------------------------------
    logger.info("STEP 1: Συγχρονισμός ιστορικού...")
    inserted_count = importer.sync_history()
    logger.info("Εισήχθησαν %d νέες κληρώσεις από CSV.", inserted_count)

    # -------------------------------------------------
    # STEP 2 — Ανάκτηση και αποθήκευση της τελευταίας κλήρωσης
    # -------------------------------------------------
    logger.info("STEP 2: Fetching latest draw...")
    latest = importer.fetch_latest_draw()

    if latest:
        inserted = db.insert_draw(latest)
        if inserted:
            logger.info("New draw saved: %s | Primary: %s | Euro: %s",
                        latest["draw_date"], latest["primary_numbers"], latest["euro_numbers"])
            inserted_count += 1
        else:
            logger.info("Draw %s already exists in database.", latest["draw_date"])
        
        # 🔮 Αξιολόγηση της προηγούμενης πρόβλεψης ΠΑΝΤΑ (όχι μόνο αν μπήκε νέα)
        db.validate_latest_prediction(latest)
    else:
        logger.warning("Could not fetch latest draw. Using existing database data.")

    # -------------------------------------------------
    # Έλεγχος αν υπάρχουν κληρώσεις στη βάση
    # -------------------------------------------------
    all_draws = db.get_all_draws()
    if not all_draws:
        logger.error("ΣΦΑΛΜΑ: Η βάση δεν περιέχει κληρώσεις.")
        sys.exit(1)

    latest_draw = all_draws[0]

    # -------------------------------------------------
    # STEP 3 — Έλεγχος προηγούμενης πρόβλεψης για το logging/email
    # -------------------------------------------------
    logger.info("STEP 3: Έλεγχος προηγούμενης πρόβλεψης...")
    validation_result = db.validate_prediction_for_draw(latest_draw)

    if validation_result:
        logger.info("==============================================")
        logger.info("📊 ΑΠΟΤΕΛΕΣΜΑΤΑ ΠΡΟΗΓΟΥΜΕΝΗΣ ΠΡΟΒΛΕΨΗΣ")
        logger.info("Κλήρωση: %s", latest_draw["draw_date"])
        logger.info("Προβλεφθέντες: %s", validation_result.get("predicted_primary"))
        logger.info("Πραγματικοί:   %s", latest_draw["primary_numbers"])
        logger.info("✅ Σωστοί κύριοι: %d/5 — %s",
                    validation_result["main_hits_count"],
                    validation_result["matched_main_numbers"])
        logger.info("Προβλεφθέντα Euro: %s", validation_result.get("predicted_euro"))
        logger.info("Πραγματικά Euro:   %s", latest_draw["euro_numbers"])
        logger.info("✅ Σωστά Euro: %d/2 — %s",
                    validation_result["euro_hits_count"],
                    validation_result["matched_euro_numbers"])
        logger.info("🎯 Στόχος ≥3: %s", "ΕΠΙΤΥΧΙΑ ✅" if validation_result["target_achieved"] else "ΑΠΩΛΕΙΑ ❌")
        logger.info("📈 Βαθμολογία: %.2f%%", validation_result["score_percentage"])
        logger.info("==============================================")
    else:
        logger.warning("Δεν υπάρχει αποθηκευμένη πρόβλεψη για την κλήρωση %s.", latest_draw["draw_date"])

    # -------------------------------------------------
    # STEP 4 — Ημερομηνία επόμενης κλήρωσης
    # -------------------------------------------------
    next_draw_date = importer.get_next_draw_date()
    logger.info("STEP 4: Ημερομηνία επόμενης κλήρωσης = %s", next_draw_date)

    # -------------------------------------------------
    # ✅ Αποφυγή διπλής πρόβλεψης
    # -------------------------------------------------
    if db.prediction_exists(next_draw_date):
        logger.warning("Πρόβλεψη υπάρχει ήδη για %s.", next_draw_date)
        logger.warning("Δεν θα δημιουργηθεί διπλή πρόβλεψη.")
        logger.warning("Δεν θα σταλεί διπλό email.")
        return

    # -------------------------------------------------
    # STEP 5 — Δημιουργία νέας πρόβλεψης
    # -------------------------------------------------
    logger.info("STEP 5: Δημιουργία πρόβλεψης...")
    freq_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = PatternAnalyzer(db)
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer)

    prediction = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    primary_candidates = prediction.get("primary_candidates", [])
    euro_candidates = prediction.get("euro_candidates", [])

    if len(primary_candidates) != 7:
        logger.error("Ο υπολογιστής δεν επέστρεψε ακριβώς 7 αριθμούς.")
        sys.exit(1)
    if len(euro_candidates) != 3:
        logger.error("Ο υπολογιστής δεν επέστρεψε ακριβώς 3 αριθμούς Euro.")
        sys.exit(1)

    logger.info("✅ Πρόβλεψη δημιουργήθηκε:")
    logger.info("   Κύριοι (7): %s", primary_candidates)
    logger.info("   Euro (3):   %s", euro_candidates)

    # -------------------------------------------------
    # STEP 6 — Αποθήκευση πρόβλεψης
    # -------------------------------------------------
    prediction_record = {
        "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw_date,
        "predicted_primary": primary_candidates,
        "predicted_euro": euro_candidates,
        "method": prediction.get("method", "composite_freq_delay"),
        "confidence": prediction.get("confidence", {}),
    }

    prediction_saved = db.insert_prediction(prediction_record)
    if not prediction_saved:
        logger.warning("⚠️ Η πρόβλεψη ΔΕΝ αποθηκεύτηκε.")
        logger.warning("Δεν θα σταλεί email.")
        return

    logger.info("✅ Η πρόβλεψη αποθηκεύτηκε για %s.", next_draw_date)

    # -------------------------------------------------
    # STEP 7 — Αποστολή EMAIL
    # -------------------------------------------------
    logger.info("STEP 7: Αποστολή email...")

    prediction_data = {
        "prediction_for_date": next_draw_date,
        "primary_candidates": primary_candidates,
        "euro_candidates": euro_candidates,
        "method": prediction.get("method", "composite_freq_delay"),
        "confidence": prediction.get("confidence", {}),
    }

    stats = {
        "total_draws": len(all_draws),
        "latest_draw": latest_draw,
        "validation": validation_result,
    }

    send_prediction_email(prediction_data, stats)

    # -------------------------------------------------
    # STEP 8 — Δημιουργία Αναφοράς/Dashboard
    # -------------------------------------------------
    logger.info("STEP 8: Δημιουργία αναφοράς...")
    try:
        from src.analytics.dashboard import SuccessDashboard
        dashboard = SuccessDashboard(db)
        dashboard.generate_html_report()
        logger.info("✅ Η αναφορά δημιουργήθηκε.")
    except Exception as exc:
        logger.warning("⚠️ Η δημιουργία αναφοράς απέτυχε: %s", exc)

    # -------------------------------------------------
    # ΟΛΟΚΛΗΡΩΣΗ
    # -------------------------------------------------
    logger.info("==================================================")
    logger.info("✅ Η ΔΙΑΔΙΚΑΣΙΑ ΟΛΟΚΛΗΡΩΘΗΚΕ")
    logger.info("Νέες κληρώσεις:   %d", inserted_count)
    logger.info("Έλεγχος προηγούμενης: %s", "✅" if validation_result else "❌")
    logger.info("Νέα πρόβλεψη:        ✅ Δημιουργήθηκε")
    logger.info("==================================================")


if __name__ == "__main__":
    run_pipeline()
