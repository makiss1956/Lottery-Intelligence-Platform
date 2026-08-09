import os
import sys
from pathlib import Path

# Προσθήκη του project root στο sys.path για σωστή επίλυση των imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.database.database_manager import DatabaseManager
from src.importers.eurojackpot_importer import EuroJackpotImporter
from src.notifications.email_notifier import EmailNotifier


def run_pipeline():
    print("--- Starting Lottery Intelligence Pipeline ---")
    
    # Αρχικοποίηση Βάσης Δεδομένων
    db_mgr = DatabaseManager()
    db_mgr.initialize_database()
    
    # 1. Fetch latest draw
    importer = EuroJackpotImporter()
    draw_data = importer.fetch_latest_draw()
    
    if draw_data:
        print(f"Successfully fetched draw for {draw_data.get('draw_date')}")
        print(f"Main Numbers: {draw_data.get('numbers')}")
        print(f"Euro Numbers: {draw_data.get('euro_numbers')}")
        
        # 2. Αποθήκευση στη Βάση Δεδομένων
        db_mgr.insert_draw(draw_data)
        print(f"✅ Stored draw for {draw_data.get('draw_date')}")
        
        # 3. Prepare report and send email notification
        notifier = EmailNotifier()
        subject = f"Eurojackpot Update: Draw {draw_data.get('draw_date')}"
        body = (
            f"Latest Eurojackpot Results:\n"
            f"Date: {draw_data.get('draw_date')}\n"
            f"Numbers: {draw_data.get('numbers')}\n"
            f"Euro Numbers: {draw_data.get('euro_numbers')}\n\n"
            f"Automated report from Lottery Intelligence Platform."
        )
        
        notifier.send_report(subject, body)
    else:
        print("⚠️ Failed to fetch latest draw data.")

if __name__ == "__main__":
    run_pipeline()
