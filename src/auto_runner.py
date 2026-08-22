import os
import json
import requests
from datetime import datetime, timedelta
from src.database.db_manager import DBManager
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.predictor import ProbabilityPredictor

OPAP_URL = "https://opap.gr"
LOG_FILE = "exports/predictions_history.md"

def fetch_opap_eurojackpot() -> dict:
    """Ανάκτηση κλήρωσης από ΟΠΑΠ και μετατροπή στη μορφή του DBManager."""
    try:
        response = requests.get(OPAP_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Μετατροπή ημερομηνίας ISO (π.χ. 2026-03-24T21:00:00) σε YYYY-MM-DD
            raw_date = data.get("drawTime", "")
            draw_date = raw_date.split("T")[0] if "T" in raw_date else raw_date
            
            return {
                "draw_date": draw_date,
                "primary_numbers": data['winningNumbers']['list'],
                "euro_numbers": data['winningNumbers']['bonus']
            }
    except Exception as e:
        print(f"❌ Σφάλμα κατά την κλήση του OPAP API: {e}")
    return None

def check_and_log_performance(db: DBManager, latest_draw: dict):
    """Έλεγχος της προηγούμενης πρόβλεψης από τη βάση και εγγραφή στο Markdown ημερολόγιο."""
    os.makedirs("exports", exist_ok=True)
    
    # Παίρνουμε την τελευταία καταγεγραμμένη πρόβλεψη από τη βάση δεδομένων σας
    predictions = db.get_predictions(limit=1)
    if not predictions:
        print("ℹ️ Δεν βρέθηκε προηγούμενη πρόβλεψη στη βάση για αξιολόγηση.")
        return

    last_pred = predictions[0]
    
    # Έλεγχος αν η πρόβλεψη προοριζόταν όντως για αυτή την ημερομηνία κλήρωσης
    if last_pred["for_draw_date"] != latest_draw["draw_date"]:
        print(f"ℹ️ Η τελευταία πρόβλεψη ήταν για τις {last_pred['for_draw_date']}, αλλά η κλήρωση είναι για τις {latest_draw['draw_date']}. Παράκαμψη αξιολόγησης.")
        return

    # Υπολογισμός επιτυχιών (Σύγκριση λιστών)
    pred_primary = last_pred["predicted_primary"]
    pred_euro = last_pred["predicted_euro"]
    
    correct_primary = list(set(pred_primary).intersection(latest_draw["primary_numbers"]))
    correct_euro = list(set(pred_euro).intersection(latest_draw["euro_numbers"]))

    # Δημιουργία/Ενημέρωση του Markdown αρχείου (Ημερολόγιο)
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"## 📅 Κλήρωση Eurojackpot: {latest_draw['draw_date']}\n")
        log.write(f"* **Πραγματικά Νούμερα:** {latest_draw['primary_numbers']} | **Euro:** {latest_draw['euro_numbers']}\n")
        log.write(f"* **Πρόβλεψη Μοντέλου:** {pred_primary} | **Euro:** {pred_euro}\n")
        log.write(f"* **Επιτυχίες:** **{len(correct_primary)}/5** Κύρια ({correct_primary}) και **{len(correct_euro)}/2** Euro ({correct_euro})\n")
        log.write(f"* **Μέθοδος:** `{last_pred['method']}`\n")
        log.write("-" * 50 + "\n\n")
    print("📝 Το ημερολόγιο επιτυχιών (predictions_history.md) ενημερώθηκε επιτυχώς!")

def run_pipeline():
    db = DBManager()
    
    # 1. Λήψη δεδομένων
    latest_draw = fetch_opap_eurojackpot()
    if not latest_draw:
        print("❌ Αδυναμία λήψης δεδομένων από το API.")
        return

    print(f"🔄 Επεξεργασία κλήρωσης ημερομηνίας: {latest_draw['draw_date']}")
    
    # 2. Αξιολόγηση παλιάς πρόβλεψης ΠΡΙΝ βάλουμε τη νέα κλήρωση στη βάση
    check_and_log_performance(db, latest_draw)

    # 3. Εισαγωγή της νέας κλήρωσης στη βάση (χρησιμοποιώντας τη μέθοδό σας)
    is_new = db.insert_draw(latest_draw)
    if not is_new:
        print("ℹ️ Η κλήρωση αυτή υπάρχει ήδη στη βάση δεδομένων. Δεν απαιτείται νέα πρόβλεψη.")
        return
    print("✅ Η νέα κλήρωση καταχωρήθηκε στη βάση δεδομένων SQLite!")

    # 4. Παραγωγή Νέας Πρόβλεψης για την Επόμενη Κλήρωση
    # Αρχικοποίηση του FrequencyAnalyzer περνώντας του το db instance
    fa = FrequencyAnalyzer(db) 
    
    # Αρχικοποίηση του Predictor με τον analyzer
    predictor = ProbabilityPredictor(frequency_analyzer=fa)
    
    # Παραγωγή υποψηφίων (7 κύρια, 3 euro)
    prediction_results = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    
    # Υπολογισμός επόμενης πιθανής ημερομηνίας κλήρωσης (Τρίτη ή Παρασκευή)
    current_date = datetime.strptime(latest_draw["draw_date"], "%Y-%m-%d")
    next_draw_date = (current_date + timedelta(days=3 if current_date.weekday() == 1 else 4)).strftime("%Y-%m-%d")

    # Προετοιμασία για εισαγωγή στον πίνακα predictions της βάσης σας
    prediction_payload = {
        "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "for_draw_date": next_draw_date,
        "predicted_primary": prediction_results["primary_candidates"],
        "predicted_euro": prediction_results["euro_candidates"],
        "method": prediction_results["method"],
        "confidence": prediction_results["confidence"]
    }
    
    # Αποθήκευση στη βάση δεδομένων (χρησιμοποιώντας τη δική σας insert_prediction)
    db.insert_prediction(prediction_payload)
    print(f"🔮 Η νέα πρόβλεψη για τις {next_draw_date} αποθηκεύτηκε στη βάση!")

if __name__ == "__main__":
    run_pipeline()
