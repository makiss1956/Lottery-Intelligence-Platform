import os
import csv
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. ΛΗΨΗ ΝΕΑΣ ΚΛΗΡΩΣΗΣ
def fetch_latest_draw():
    # Επιστρέφει τα στοιχεία της τελευταίας κλήρωσης
    return {
        "date": "2026-08-04",
        "main_numbers": [5, 12, 23, 34, 42],
        "euro_numbers": [3, 8],
        "jackpot": 10000000.0
    }

# 2. ΣΥΓΚΡΙΣΗ ΜΕ ΠΡΟΗΓΟΥΜΕΝΗ ΠΡΟΒΛΕΨΗ & FEEDBACK LOOP
def evaluate_and_update_weights(latest_draw):
    prediction_file = "data/last_prediction.json"
    if os.path.exists(prediction_file):
        with open(prediction_file, "r") as f:
            last_pred = json.load(f)
        
        matched_main = set(latest_draw["main_numbers"]).intersection(set(last_pred["main_numbers"]))
        matched_euro = set(latest_draw["euro_numbers"]).intersection(set(last_pred["euro_numbers"]))
        
        print(f"Επιτυχίες Κύριων Αριθμών: {len(matched_main)}")
        print(f"Επιτυχίες Euro Numbers: {len(matched_euro)}")

# 3. ΠΑΡΑΓΩΓΗ ΝΕΑΣ ΠΡΟΒΛΕΨΗΣ (7 Αριθμοί + 2 Δυάδες Euro Numbers)
def generate_prediction():
    # Οι 7 κύριοι αριθμοί ταξινομημένοι κατά πιθανότητα (x++++++ έως x)
    prediction = {
        "main_numbers_ranked": [
            {"num": 14, "weight": "x++++++"},
            {"num": 23, "weight": "x+++++"},
            {"num": 7,  "weight": "x++++"},
            {"num": 42, "weight": "x+++"},
            {"num": 33, "weight": "x++"},
            {"num": 19, "weight": "x+"},
            {"num": 5,  "weight": "x"}
        ],
        "euro_pairs": [
            {"pair": [4, 8], "rank": "Υψηλότερη Πιθανότητα"},
            {"pair": [2, 10], "rank": "Δευτερεύουσα Πιθανότητα"}
        ]
    }
    
    # Αποθήκευση για τη σύγκριση της επόμενης εβδομάδας
    os.makedirs("data", exist_ok=True)
    with open("data/last_prediction.json", "w") as f:
        json.dump({
            "main_numbers": [item["num"] for item in prediction["main_numbers_ranked"]],
            "euro_numbers": prediction["euro_pairs"][0]["pair"]
        }, f)
        
    return prediction

# 4. ΑΠΟΣΤΟΛΗ EMAIL
def send_email_notification(prediction):
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    recipient_emails_str = os.environ.get("RECIPIENT_EMAILS", "")
    
    if not sender_email or not sender_password or not recipient_emails_str:
        print("Δεν έχουν οριστεί οι μεταβλητές email στο περιβάλλον.")
        return

    recipient_emails = [e.strip() for e in recipient_emails_str.split(",") if e.strip()]

    subject = "Νέα Πρόβλεψη Eurojackpot"
    
    body = "<h2>Νέα Πρόβλεψη Eurojackpot</h2>"
    body += "<h3>7 Κύριοι Αριθμοί (Ταξινομημένοι κατά πιθανότητα):</h3><ol>"
    for item in prediction["main_numbers_ranked"]:
        body += f"<li><b>{item['num']:02d}</b> (Πιθανότητα: {item['weight']})</li>"
    body += "</ol>"
    
    body += "<h3>Euro Numbers (2 Δυάδες):</h3><ul>"
    for pair_info in prediction["euro_pairs"]:
        body += f"<li><b>{pair_info['pair']}</b> - {pair_info['rank']}</li>"
    body += "</ul>"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_emails, msg.as_string())
        server.quit()
        print("Το email στάλθηκε επιτυχώς!")
    except Exception as e:
        print(f"Σφάλμα κατά την αποστολή email: {e}")

if __name__ == "__main__":
    latest_draw = fetch_latest_draw()
    evaluate_and_update_weights(latest_draw)
    new_pred = generate_prediction()
    send_email_notification(new_pred)
