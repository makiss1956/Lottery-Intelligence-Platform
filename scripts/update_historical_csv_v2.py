"""
Update Eurojackpot Historical CSV (Last 2 Years).

Fetches historical Eurojackpot draw results via web scraping,
restricting the range to the last 2 years for fast execution,
and updates data/eurojackpot_raw_history.csv.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Path setup για standalone execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.importers.web_scraper import EurojackpotWebScraper

logger = get_logger("UpdateHistoricalCSV")


def get_target_years() -> List[int]:
    """
    Περιορισμός στα 2 τελευταία έτη.
    Επιστρέφει [τρέχον_έτος - 1, τρέχον_έτος] (π.χ. [2025, 2026]).
    """
    current_year = datetime.now().year
    return [current_year - 1, current_year]


def load_existing_csv(csv_path: Path) -> Dict[str, Dict[str, str]]:
    """Load existing draws from CSV mapped by Date (YYYY-MM-DD)."""
    existing_draws = {}
    if not csv_path.exists():
        return existing_draws

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                date_val = row.get("Date", "").strip()
                if date_val:
                    existing_draws[date_val] = row
    except Exception as exc:
        logger.error("Error reading existing CSV: %s", exc)

    return existing_draws


def main():
    csv_path = project_root / "data" / "eurojackpot_raw_history.csv"
    existing_draws = load_existing_csv(csv_path)
    logger.info("Loaded %d existing draws from CSV.", len(existing_draws))

    target_years = get_target_years()
    logger.info("Scraping draws for years: %s", target_years)

    scraper = EurojackpotWebScraper()
    scraped_count = 0
    updated_count = 0

    for year in target_years:
        logger.info("Fetching draws for year %d...", year)
        year_draws = scraper.fetch_year_draws(year)
        
        for draw in year_draws:
            scraped_count += 1
            draw_date = draw["draw_date"]
            
            # Μορφοποίηση σε CSV row
            row_dict = {
                "Date": draw_date,
                "N1": str(draw["primary_numbers"][0]),
                "N2": str(draw["primary_numbers"][1]),
                "N3": str(draw["primary_numbers"][2]),
                "N4": str(draw["primary_numbers"][3]),
                "N5": str(draw["primary_numbers"][4]),
                "E1": str(draw["euro_numbers"][0]),
                "E2": str(draw["euro_numbers"][1]),
            }

            # Ενημέρωση ή προσθήκη νέας εγγραφής
            if draw_date not in existing_draws or existing_draws[draw_date] != row_dict:
                existing_draws[draw_date] = row_dict
                updated_count += 1

    # Ταξινόμηση ανά ημερομηνία (φθίνουσα)
    sorted_dates = sorted(existing_draws.keys(), reverse=True)

    # Εγγραφή πίσω στο CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["Date", "N1", "N2", "N3", "N4", "N5", "E1", "E2"]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for d in sorted_dates:
            writer.writerow(existing_draws[d])

    logger.info(
        "Finished updating CSV | Total in CSV=%d | Scraped=%d | New/Updated=%d",
        len(existing_draws),
        scraped_count,
        updated_count,
    )


if __name__ == "__main__":
    main()
