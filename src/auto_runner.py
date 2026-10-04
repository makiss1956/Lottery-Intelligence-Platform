import os
import json
from datetime import datetime, timezone
from src.database.db_manager import DBManager
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.predictor import ProbabilityPredictor
from src.importers.eurojackpot_importer import EurojackpotImporter

LOG_FILE = "exports/predictions_history.md"


def check_and_log_performance(db: DBManager, latest_draw: dict):
    """Έλεγχος της προηγούμενης πρόβλεψης από τη βάση και εγγραφή στο Markdown ημερολόγιο."""
    os.makedirs("exports", exist_ok=True)
    
    predictions = db.get_predictions(limit=1)
    if not predictions:
        print("ℹ️ Δεν βρέθηκε προηγούμενη πρόβλεψη στη βάση για αξιολόγηση.")
        return

    last_pred = predictions[0]
    
    # Έλεγχος αν η πρόβλεψη προοριζόταν όντως για αυτή την ημερομηνία κλήρωσης
    if last_pred.get("for_draw_date") != latest_draw["draw_date"]:
        print(f"ℹ️ Η τελευταία πρόβλεψη ήταν για τις {last_pred.get('for_draw_date')}, αλλά η κλήρωση είναι για τις {latest_draw['draw_date']}. Παράκαμψη αξιολόγησης.")
        return

    # Υπολογισμός επιτυχιών (Σύγκριση λιστών)
    pred_primary = last_pred.get("predicted_primary", [])
    pred_euro = last_pred.get("predicted_euro", [])
    
    correct_primary = list(set(pred_primary).intersection(latest_draw["primary_numbers"]))
    correct_euro = list(set(pred_euro).intersection(latest_draw["euro_numbers"]))

    # Δημιουργία/Ενημέρωση του Markdown αρχείου (Ημερολόγιο)
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"## 📅 Κλήρωση Eurojackpot: {latest_draw['draw_date']}\n")
        log.write(f"* **Πραγματικά Νούμερα:** {latest_draw['primary_numbers']} | **Euro:** {latest_draw['euro_numbers']}\n")
        log.write(f"* **Πρόβλεψη Μοντέλου:** {pred_primary} | **Euro:** {pred_euro}\n")
        log.write(f"* **Επιτυχίες:** **{len(correct_primary)}/5** Κύρια ({correct_primary}) και **{len(correct_euro)}/2** Euro ({correct_euro})\n")
        log.write(f"* **Μέθοδος:** `{last_pred.get('method', 'N/A')}`\n")
        log.write("-" * 50 + "\n\n")
        
    print("📝 Το ημερολόγιο επιτυχιών (predictions_history.md) ενημερώθηκε επιτυχώς!")


def run_pipeline():
    db = DBManager()
    importer = EurojackpotImporter(db_manager=db)
    
    # 1. Λήψη τελευταίας κλήρωσης (μέσω του Importer για ασφάλεια & fallbacks)
    latest_draw = importer.fetch_latest_draw()
    if not latest_draw:
        print("❌ Αδυναμία λήψης δεδομένων κλήρωσης.")
        return

    print(f"🔄 Επεξεργασία κλήρωσης ημερομηνίας: {latest_draw['draw_date']}")
    
    # 2. Αξιολόγηση παλιάς πρόβλεψης ΠΡΙΝ καταχωρηθεί η νέα κλήρωση
    check_and_log_performance(db, latest_draw)

    # 3. Εισαγωγή της νέας κλήρωσης στη βάση
    is_new = db.insert_draw(latest_draw)
    if not is_new:
        print("ℹ️ Η κλήρωση αυτή υπάρχει ήδη στη βάση δεδομένων. Δεν απαιτείται νέα πρόβλεψη.")
        return
        
    print("✅ Η νέα κλήρωση καταχωρήθηκε στη βάση δεδομένων!")

    # 4. Παραγωγή Νέας Πρόβλεψης για την Επόμενη Κλήρωση
    fa = FrequencyAnalyzer(db) 
    predictor = ProbabilityPredictor(frequency_analyzer=fa)
    
    # Παραγωγή υποψηφίων (7 κύρια, 3 euro)
    prediction_results = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    
    # Υπολογισμός επόμενης ημερομηνίας κλήρωσης (Τρίτη ή Παρασκευή)
    next_draw_date = importer.get_next_draw_date()

    # Προετοιμασία payload
    prediction_payload = {
        "prediction_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw_date,
        "predicted_primary": prediction_results["primary_candidates"],
        "predicted_euro": prediction_results["euro_candidates"],
        "method": prediction_results["method"],
        "confidence": prediction_results["confidence"]
    }
    
    # Αποθήκευση στη βάση δεδομένων
    db.insert_prediction(prediction_payload)
    print(f"🔮 Η νέα πρόβλεψη για τις {next_draw_date} αποθηκεύτηκε στη βάση!")


if __name__ == "__main__":
    run_pipeline()
