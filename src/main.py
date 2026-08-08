import sys
import os

# Ensure src directory is in Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from importer.eurojackpot_importer import EurojackpotImporter
from notifications.email_notifier import EmailNotifier

def run_pipeline():
    print("--- Starting Lottery Intelligence Pipeline ---")
    
    # 1. Fetch latest draw
    importer = EurojackpotImporter()
    draw_data = importer.fetch_latest_draw()
    
    if draw_data:
        print(f"Successfully fetched draw for {draw_data.get('draw_date')}")
        print(f"Main Numbers: {draw_data.get('numbers')}")
        print(f"Euro Numbers: {draw_data.get('euro_numbers')}")
        
        # 2. Prepare report and send email notification
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
        print("Failed to fetch latest draw data.")

if __name__ == "__main__":
    run_pipeline()
