import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def send_email():
    user = os.getenv("EMAIL_USER")
    to = os.getenv("EMAIL_TO")
    password = os.getenv("EMAIL_PASS")

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = f"Πρόβλεψη Eurojackpot — {datetime.now().strftime('%d/%m/%Y')}"

    # Διάβασε την πρόβλεψη από το αρχείο αναφοράς
    try:
        with open("reports/latest_prediction.txt", "r", encoding="utf-8") as f:
            body = f.read()
    except:
        body = "Η πρόβλεψη και η σύγκριση προηγούμενης βρίσκονται στο αποθετήριο:\nhttps://github.com/makiss1956/Lottery-Intelligence-Platform"

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Αποστολή μέσω Gmail (αν χρησιμοποιείς Gmail)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.send_message(msg)

if __name__ == "__main__":
    send_email()
    print("✅ Email απεστάλη με επιτυχία!")
