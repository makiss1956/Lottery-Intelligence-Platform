"""
Main Execution Pipeline for Lottery Intelligence Platform.
Pipeline:
1. Synchronize CSV history with database.
2. Detect whether a new draw was added.
3. Validate the prediction assigned to that draw.
4. Determine next draw date.
5. Generate predictions using multiple methods (Hybrid Ensemble).
6. Save prediction.
7. Send email for the new prediction.
8. Generate dashboard.
"""
import sys
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# ✅ ΔΙΟΡΘΩΣΗ: Path setup για να τρέχει σωστά ως script
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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

    msg = MIMEMultipart("alternative")
    msg["From"] = email_user
    msg["To"] = email_to
    msg["Subject"] = f"🎯 Πρόβλεψη Eurojackpot — {prediction_data['prediction_for_date']}"

    body = f"""
Αυτόματο μήνυμα από το Lottery Intelligence Platform
======================================================

📅 Πρόβλεψη για κλήρωση: {prediction_data['prediction_for_date']}

🔢 Προτεινόμενοι αριθμοί (7 κύριοι):
{', '.join(map(str, prediction_data['primary_candidates']))}

💶 Προτεινόμενοι αριθμοί Euro (3):
{', '.join(map(str, prediction_data['euro_candidates']))}

📊 Μέθοδος: {prediction_data.get('method', 'hybrid_ensemble')}

📈 Στατιστικά:
- Σύνολο κληρώσεων: {stats['total_draws']}
- Τελευταία κλήρωση: {stats['latest_draw']['draw_date']}

"""

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
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        logger.info(f"📧 Email απεστάλη με επιτυχία προς: {email_to}")
        return True
    except Exception as e:
        logger.error(f"❌ Αποτυχία αποστολής email: {str(e)}")
        return False


def _ensure_count(candidates, sorted_pool, target_count):
    """
    ✅ ΒΟΗΘΗΤΙΚΗ: Εξασφαλίζει ότι έχουμε ακριβώς target_count μοναδικούς αριθμούς.
    Συμπληρώνει από το sorted_pool αν λείπουν.
    """
    seen = set()
    result = []
    for n in candidates:
        if n not in seen:
            result.append(n)
            seen.add(n)
    # Συμπλήρωση αν λείπουν
    for num, _ in sorted_pool:
        if num not in seen:
            result.append(num)
            seen.add(num)
            logger.info("✅ Συμπληρώθηκε ο αριθμός: %s", num)
            if len(result) == target_count:
                break
    return sorted(result[:target_count])


def run_pipeline() -> None:
    """Execute the complete lottery intelligence pipeline."""
    logger.info("=" * 50)
    logger.info("STARTING LOTTERY INTELLIGENCE PIPELINE")
    logger.info("=" * 50)

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
    # STEP 3 — Έλεγχος προηγούμενης πρόβλεψης
    # -------------------------------------------------
    logger.info("STEP 3: Έλεγχος προηγούμενης πρόβλεψης...")
    validation_result = db.validate_prediction_for_draw(latest_draw)

    if validation_result:
        logger.info("=" * 46)
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
        logger.info("=" * 46)
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
    # STEP 5 — Αναλύσεις & Παραγωγή Πρόβλεψης (Multi-Method Hybrid)
    # -------------------------------------------------
    logger.info("STEP 5: Generating predictions using multiple methods...")

    freq_analyzer = FrequencyAnalyzer(db)
    pattern_analyzer = PatternAnalyzer(db)

    # Method A: Original Composite Predictor
    predictor = ProbabilityPredictor(freq_analyzer, pattern_analyzer)
    pred_original = predictor.predict_candidate_set(primary_count=7, euro_count=3)

    # Method B: Seeded RNG
    from src.analytics.seeded_rng import SeededRNGGenerator
    rng = SeededRNGGenerator(seed_source="stats")
    rng.set_seed_from_stats(freq_analyzer.get_primary_frequencies())
    rng_primary = rng.generate_weighted(
        freq_analyzer.get_primary_frequencies(),
        count=7, total_pool=50
    )
    rng_euro = rng.generate_weighted(
        freq_analyzer.get_euro_frequencies(),
        count=3, total_pool=12
    )

    # Method C: Temperature Mix
    from src.analytics.temperature_analyzer import TemperatureAnalyzer
    temp = TemperatureAnalyzer(db)
    temp_result = temp.get_mixed_candidates(hot_ratio=0.4, warm_ratio=0.4, cold_ratio=0.2)

    # Method D: Monte Carlo
    from src.analytics.monte_carlo import MonteCarloSimulator
    mc = MonteCarloSimulator(freq_analyzer, simulations=5000)
    mc_result = mc.run_simulation()

    # ✅ ΔΙΟΡΘΩΣΗ: Combine all methods (hybrid approach) — συμπεριλαμβάνεται Monte Carlo
    all_primary = (
        pred_original["primary_candidates"][:3] +
        rng_primary[:2] +
        temp_result.get("primary_candidates", [])[:2] +
        mc_result.get("primary_candidates", [])[:2]  # ✅ ΠΡΟΣΘΗΚΗ: Monte Carlo συνεισφέρει
    )

    # ✅ ΔΙΟΡΘΩΣΗ: Fallback — εξασφαλίζει ακριβώς 7 μοναδικούς
    primary_candidates = _ensure_count(
        all_primary,
        sorted(pred_original.get("primary_scores", {}).items(), key=lambda x: x[1], reverse=True),
        7
    )

    # Euro: use original + RNG + temperature + Monte Carlo
    all_euro = (
        pred_original["euro_candidates"][:2] +
        rng_euro[:2] +
        temp_result.get("euro_candidates", [])[:2] +
        mc_result.get("euro_candidates", [])[:2]  # ✅ ΠΡΟΣΘΗΚΗ: Monte Carlo συνεισφέρει
    )

    # ✅ ΔΙΟΡΘΩΣΗ: Fallback — εξασφαλίζει ακριβώς 3 μοναδικούς
    euro_candidates = _ensure_count(
        all_euro,
        sorted(pred_original.get("euro_scores", {}).items(), key=lambda x: x[1], reverse=True),
        3
    )

    logger.info("Hybrid prediction generated | Primary: %s | Euro: %s", primary_candidates, euro_candidates)

    if len(primary_candidates) != 7:
        logger.error("Ο υπολογιστής δεν επέστρεψε ακριβώς 7 αριθμούς.")
        sys.exit(1)
    if len(euro_candidates) != 3:
        logger.error("Ο υπολογιστής δεν επέστρεψε ακριβώς 3 αριθμούς Euro.")
        sys.exit(1)

    # -------------------------------------------------
    # STEP 6 — Αποθήκευση πρόβλεψης
    # -------------------------------------------------
    prediction_record = {
        "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw_date,
        "predicted_primary": primary_candidates,
        "predicted_euro": euro_candidates,
        "method": "hybrid_ensemble_v2",
        "confidence": pred_original.get("confidence", {}),
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
        "method": "hybrid_ensemble_v2",
        "confidence": pred_original.get("confidence", {}),
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
    logger.info("=" * 50)
    logger.info("✅ Η ΔΙΑΔΙΚΑΣΙΑ ΟΛΟΚΛΗΡΩΘΗΚΕ")
    logger.info("Νέες κληρώσεις:   %d", inserted_count)
    logger.info("Έλεγχος προηγούμενης: %s", "✅" if validation_result else "❌")
    logger.info("Νέα πρόβλεψη:        ✅ Δημιουργήθηκε")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_pipeline()
