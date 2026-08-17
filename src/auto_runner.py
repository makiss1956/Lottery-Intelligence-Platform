import os
import json
import requests
from datetime import datetime
from src.analytics.predictor import ProbabilityPredictor
# Σημείωση: Αντικαταστήστε τις παρακάτω γραμμές με τους πραγματικούς σας imports για τον Frequency Analyzer
# από το δικό σας src.analytics επίπεδο.
# from src.analytics.frequency_analyzer import FrequencyAnalyzer 
# from src.database.manager import DatabaseManager

OPAP_URL = "https://opap.gr" # Παράδειγμα για Eurojackpot
PRED_FILE = "exports/next_eurojackpot_prediction.json"
LOG_FILE = "exports/predictions_history.md"

def fetch_latest_draw():
    """Ανάκτηση τελευταίας κλήρωσης από το επίσημο API του ΟΠΑΠ χωρίς block."""
    try:
        response = requests.get(OPAP_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "draw_id": data['drawId'],
                "numbers": data['winningNumbers']['list'],
                "bonus": data['winningNumbers']['bonus'],
                "date": data['drawTime']
            }
    except Exception as e:
        print(f"Σφάλμα API: {e}")
    return None

def log_and_evaluate(actual_draw):
    """Σύγκριση προηγούμενης πρόβλεψης με τα αποτελέσματα και καταγραφή στο ημερολόγιο."""
    os.makedirs("exports", exist_ok=True)
    
    if os.path.exists(PRED_FILE):
        with open(PRED_FILE, "r", encoding="utf-8") as f:
            old_pred = json.load(f)
        
        # Έλεγχος αν έχουμε ήδη αξιολογήσει αυτή την κλήρωση
        if old_pred.get("evaluated_draw_id") == actual_draw["draw_id"]:
            print("Η κλήρωση αυτή έχει ήδη αξιολογηθεί.")
            return False

        pred_primary = old_pred.get("primary_candidates", [])
        pred_euro = old_pred.get("euro_candidates", [])
        
        match_primary = list(set(pred_primary).intersection(actual_draw["numbers"]))
        match_euro = list(set(pred_euro).intersection(actual_draw["bonus"]))
        
        # Εγγραφή στο Markdown Ημερολόγιο
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"## 📅 Κλήρωση ID: {actual_draw['draw_id']} ({datetime.now().strftime('%Y-%m-%d')})\n")
            log.write(f"* **Πραγματικά Νούμερα:** {actual_draw['numbers']} | **Euro:** {actual_draw['bonus']}\n")
            log.write(f"* **Πρόβλεψη Μοντέλου:** {pred_primary} | **Euro:** {pred_euro}\n")
            log.write(f"* **Επιτυχίες:** {len(match_primary)} Κύρια ({match_primary}) και {len(match_euro)} Euro ({match_euro})\n")
            log.write("-" * 50 + "\n\n")
        print("Το ημερολόγιο επιτυχιών ενημερώθηκε.")
        return True
    return True

def generate_new_prediction():
    """Εκκίνηση του Predictor και αποθήκευση της νέας πρόβλεψης."""
    # 1. Εδώ αρχικοποιείτε τους δικούς σας αναλυτές με βάση τη βάση δεδομένων σας
    # db = DatabaseManager()
    # db.update_database_with_new_draw(actual_draw) # Προαιρετική αυτόματη ενημέρωση βάσης
    # fa = FrequencyAnalyzer(db)
    
    # Εικονική αρχικοποίηση για την ομαλή εκτέλεση του Predictor σας
    fa = None 
    predictor = ProbabilityPredictor(frequency_analyzer=fa)
    
    # Εκτέλεση της μηχανής composite scoring που μας δώσατε
    new_pred = predictor.predict_candidate_set(primary_count=7, euro_count=3)
    
    # Αποθήκευση σε JSON για την επόμενη κλήρωση
    with open(PRED_FILE, "w", encoding="utf-8") as f:
        json.dump(new_pred, f, indent=4, ensure_ascii=False)
    print("Η νέα πρόβλεψη δημιουργήθηκε και αποθηκεύτηκε.")

if __name__ == "__main__":
    draw = fetch_latest_draw()
    if draw:
        should_predict = log_and_evaluate(draw)
        if should_predict:
            generate_new_prediction()

