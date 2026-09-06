"""
Update Eurojackpot historical CSV.

Fetches the previous and current year from the OPAP API
and safely merges the results with the existing CSV.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


project_root = Path(__file__).resolve().parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from src.core.logger import get_logger
from src.importers.web_scraper import EurojackpotWebScraper


logger = get_logger("UpdateHistoricalCSV")


CSV_FIELDS = [
    "Date",
    "N1",
    "N2",
    "N3",
    "N4",
    "N5",
    "E1",
    "E2",
]


def get_target_years() -> List[int]:
    """Return current year and previous year."""

    current_year = datetime.now().year

    return [
        current_year - 1,
        current_year,
    ]


def load_existing_csv(
    csv_path: Path,
) -> Dict[str, Dict[str, str]]:
    """Load existing CSV records keyed by normalized date."""

    existing_draws: Dict[str, Dict[str, str]] = {}

    if not csv_path.exists():
        return existing_draws

    try:
        with csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:

            reader = csv.DictReader(
                file,
                delimiter=";",
            )

            for row in reader:
                date_value = row.get(
                    "Date",
                    "",
                ).strip()

                if not date_value:
                    continue

                existing_draws[date_value] = {
                    field: row.get(field, "").strip()
                    for field in CSV_FIELDS
                }

    except Exception as exc:
        logger.error(
            "Error reading existing CSV: %s",
            exc,
        )

    return existing_draws


def draw_to_csv_row(
    draw: Dict,
) -> Dict[str, str]:
    """Convert normalized draw into CSV row."""

    primary = draw["primary_numbers"]
    euro = draw["euro_numbers"]

    return {
        "Date": draw["draw_date"],
        "N1": str(primary[0]),
        "N2": str(primary[1]),
        "N3": str(primary[2]),
        "N4": str(primary[3]),
        "N5": str(primary[4]),
        "E1": str(euro[0]),
        "E2": str(euro[1]),
    }


def write_csv(
    csv_path: Path,
    draws: Dict[str, Dict[str, str]],
) -> None:
    """Write the complete merged CSV safely."""

    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = csv_path.with_suffix(".tmp")

    sorted_dates = sorted(
        draws.keys(),
        reverse=True,
    )

    with temp_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
            delimiter=";",
        )

        writer.writeheader()

        for draw_date in sorted_dates:
            writer.writerow(draws[draw_date])

    temp_path.replace(csv_path)


def main() -> int:
    """Update the historical CSV."""

    csv_path = (
        project_root
        / "data"
        / "eurojackpot_raw_history.csv"
    )

    existing_draws = load_existing_csv(
        csv_path
    )

    logger.info(
        "Loaded %d existing draws.",
        len(existing_draws),
    )

    scraper = EurojackpotWebScraper()

    total_scraped = 0
    updated_count = 0

    for year in get_target_years():

        logger.info(
            "Fetching Eurojackpot draws for year %d...",
            year,
        )

        year_draws = scraper.fetch_year_draws(
            year
        )

        total_scraped += len(year_draws)

        for draw in year_draws:

            row = draw_to_csv_row(draw)

            draw_date = draw["draw_date"]

            if (
                draw_date not in existing_draws
                or existing_draws[draw_date] != row
            ):
                existing_draws[draw_date] = row
                updated_count += 1

    if total_scraped == 0:
        logger.error(
            "OPAP returned zero valid draws. "
            "Existing CSV will NOT be modified."
        )
        return 1

    write_csv(
        csv_path,
        existing_draws,
    )

    logger.info(
        "CSV update completed | "
        "Total=%d | Scraped=%d | New/Updated=%d",
        len(existing_draws),
        total_scraped,
        updated_count,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
