"""Command Line Interface for Lottery Intelligence Platform."""
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("=" * 65)
print(" LOTTERY INTELLIGENCE PLATFORM — STATISTICAL RESEARCH TOOL")
print(" Disclaimer: For educational & analytical research only.")
print("=" * 65)

from src.analytics.predictor import ProbabilityPredictor
from src.analytics.frequency_analyzer import FrequencyAnalyzer
from src.analytics.pattern_analyzer import PatternAnalyzer
from src.database.db_manager import DBManager
from src.importers.eurojackpot_importer import EuroJackpotImporter
from src.notifications.email_sender import EmailSender
from src.main import run_pipeline
from src.core.logger import get_logger

logger = get_logger("CLI")

def cmd_predict(args):
    db = DBManager()
    analyzer = FrequencyAnalyzer(db)
    pattern = PatternAnalyzer()
    predictor = ProbabilityPredictor(analyzer, pattern)
    candidates = predictor.predict_candidate_set(primary_count=args.primary, euro_count=args.euro)
    print("\n" + "=" * 50)
    print("🎯 PREDICTION RESULT")
    print("=" * 50)
    print(f"Primary ({args.primary}): {candidates['primary_candidates']}")
    print(f"Euro ({args.euro}): {candidates['euro_candidates']}")
    print("=" * 50 + "\n")

def cmd_fetch(args):
    print("\n⏳ Fetching latest Eurojackpot draws...")
    importer = EuroJackpotImporter()
    draw = importer.fetch_latest_draw()
    if draw:
        print(f"✅ Draw found: {draw['draw_date']}")
        print(f" Primary: {draw['primary_numbers']}")
        print(f" Euro: {draw['euro_numbers']}")
    else:
        print("❌ No draw data retrieved.")

def cmd_pipeline(args):
    print("\n🚀 Launching Full Pipeline...\n")
    run_pipeline(force=args.force)

def cmd_history(args):
    db = DBManager()
    rows = db.get_prediction_history(limit=args.limit)
    print("\n📚 PREDICTION HISTORY")
    print("-" * 80)
    print(f"{'For Date':<12} {'Predicted Primary':<30} {'Predicted Euro':<20} {'Main':<6} {'Euro':<6} {'Score':<8}")
    print("-" * 80)
    for r in rows:
        pm = r.get("predicted_primary", "—")
        pe = r.get("predicted_euro", "—")
        mh = r.get("main_hits")
        eh = r.get("euro_hits")
        sc = r.get("score_percentage")
        print(f"{r.get('prediction_for_date',''):<12} {pm:<30} {pe:<20} {str(mh):<6} {str(eh):<6} {str(sc)+'%' if sc else '—':<8}")
    print("-" * 80)

def cmd_report(args):
    db = DBManager()
    rows = db.get_evaluated_predictions(limit=args.limit)
    if not rows:
        print("\nΔεν υπάρχουν αξιολογημένες προβλέψεις ακόμα.")
        print("Τρέξε πρώτα το pipeline τουλάχιστον 2 φορές (μία για πρόβλεψη, μία για αξιολόγηση).")
        return

    print("\n📊 ΑΝΑΦΟΡΑ ΠΡΟΒΛΕΨΗΣ vs ΠΡΑΓΜΑΤΙΚΟΤΗΤΑ")
    print("=" * 100)
    print(f"{'Ημ/νία':<12} {'Προβλ. Κύριοι':<25} {'Πραγμ. Κύριοι':<25} {'Κύριοι Hits':<12} {'Euro Hits':<10} {'Score':<8}")
    print("-" * 100)
    for r in rows:
        pred_main = r.get("predicted_primary", "—")
        actual_main = r.get("actual_primary", "—")
        mh = r.get("main_hits", "—")
        eh = r.get("euro_hits", "—")
        sc = r.get("score_percentage")
        print(f"{r.get('prediction_for_date',''):<12} {pred_main:<25} {actual_main:<25} {str(mh):<12} {str(eh):<10} {str(sc)+'%' if sc else '—':<8}")
    print("=" * 100)

def main():
    parser = argparse.ArgumentParser(description="Lottery Intelligence Platform CLI")
    sub = parser.add_subparsers(dest="command", help="Commands")

    sub.add_parser("run", help="Run full pipeline")

    p = sub.add_parser("predict", help="Generate prediction")
    p.add_argument("--primary", type=int, default=7)
    p.add_argument("--euro", type=int, default=3)

    sub.add_parser("fetch", help="Fetch latest draw")

    pl = sub.add_parser("pipeline", help="Run pipeline (alias for run)")
    pl.add_argument("--force", action="store_true", help="Force even if exists")

    h = sub.add_parser("history", help="Show prediction history")
    h.add_argument("--limit", type=int, default=20)

    r = sub.add_parser("report", help="Αναφορά πρόβλεψης vs πραγματικότητα")
    r.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()

    if args.command == "run" or args.command == "pipeline":
        cmd_pipeline(args)
    elif args.command == "predict":
        cmd_predict(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        # Default: run pipeline
        run_pipeline()

if __name__ == "__main__":
    main()
