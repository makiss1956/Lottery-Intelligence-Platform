"""
Update historical Eurojackpot CSV data.

The official OPAP API is the authoritative source.

This script:
1. Retrieves historical Eurojackpot draws from OPAP.
2. Preserves the project's CSV format.
3. Merges new data with existing CSV data.
4. Removes duplicate draw dates.
5. Validates every draw before saving.
6. Fails with a non-zero exit code if the API cannot provide
   usable historical data.

CSV format:
Date;N1;N2;N3;N4;N5;E1;E2;Jackpot_Euros
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List


# ----------------------------------------------------------------------
# Project paths
# ----------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------

from src.importers.web_scraper import EurojackpotWebScraper


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

CSV_PATH = ROOT_DIR / "data" / "eurojackpot_raw_history.csv"

CSV_FIELDS = [
    "Date",
    "N1",
    "N2",
    "N3",
    "N4",
    "N5",
    "E1",
    "E2",
    "Jackpot_Euros",
]


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

def validate_draw(draw: Dict[str, Any]) -> bool:
    """Validate one normalized draw."""
    try:
        draw_date = str(draw["draw_date"])

        primary = [int(number) for number in draw["primary_numbers"]]
        euro = [int(number) for number in draw["euro_numbers"]]

    except (KeyError, TypeError, ValueError):
        return False

    if len(primary) != 5:
        return False

    if len(euro) != 2:
        return False

    if len(set(primary)) != 5:
        return False

    if len(set(euro)) != 2:
        return False

    if not all(1 <= number <= 50 for number in primary):
        return False

    if not all(1 <= number <= 12 for number in euro):
        return False

    if len(draw_date) != 10:
        return False

    return True


# ----------------------------------------------------------------------
# Existing CSV
# ----------------------------------------------------------------------

def read_existing_csv() -> Dict[str, Dict[str, Any]]:
    """
    Read the existing historical CSV.

    Returns a dictionary indexed by draw date.
    Invalid rows are ignored.
    """
    existing: Dict[str, Dict[str, Any]] = {}

    if not CSV_PATH.exists():
        print(f"CSV does not exist yet: {CSV_PATH}")
        return existing

    try:
        with CSV_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:

            reader = csv.DictReader(
                csv_file,
                delimiter=";",
            )

            for row in reader:
                draw_date = (
                    row.get("Date")
                    or row.get("date")
                    or row.get("draw_date")
                )

                if not draw_date:
                    continue

                draw_date = draw_date.strip()

                try:
                    primary = [
                        int(row[f"N{i}"])
                        for i in range(1, 6)
                    ]

                    euro = [
                        int(row[f"E{i}"])
                        for i in range(1, 3)
                    ]

                except (KeyError, TypeError, ValueError):
                    continue

                draw = {
                    "draw_date": draw_date,
                    "primary_numbers": sorted(primary),
                    "euro_numbers": sorted(euro),
                    "jackpot_euros": row.get(
                        "Jackpot_Euros",
                        "",
                    ),
                }

                if validate_draw(draw):
                    existing[draw_date] = draw

    except OSError as exc:
        raise RuntimeError(
            f"Unable to read existing CSV: {exc}"
        ) from exc

    print(
        f"Existing valid CSV draws: {len(existing)}"
    )

    return existing


# ----------------------------------------------------------------------
# CSV writing
# ----------------------------------------------------------------------

def write_csv(
    draws: Dict[str, Dict[str, Any]],
) -> None:
    """Write the complete validated history to CSV."""
    CSV_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sorted_draws = sorted(
        draws.values(),
        key=lambda draw: draw["draw_date"],
    )

    temporary_path = CSV_PATH.with_suffix(".tmp")

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=CSV_FIELDS,
                delimiter=";",
            )

            writer.writeheader()

            for draw in sorted_draws:
                primary = draw["primary_numbers"]
                euro = draw["euro_numbers"]

                writer.writerow(
                    {
                        "Date": draw["draw_date"],
                        "N1": primary[0],
                        "N2": primary[1],
                        "N3": primary[2],
                        "N4": primary[3],
                        "N5": primary[4],
                        "E1": euro[0],
                        "E2": euro[1],
                        "Jackpot_Euros": draw.get(
                            "jackpot_euros",
                            "",
                        ),
                    }
                )

        temporary_path.replace(CSV_PATH)

    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink()

        raise RuntimeError(
            f"Unable to write CSV: {exc}"
        ) from exc


# ----------------------------------------------------------------------
# Historical synchronization
# ----------------------------------------------------------------------

def update_history() -> int:
    """Download and merge historical Eurojackpot draws."""
    print("=" * 70)
    print("EUROJACKPOT HISTORICAL DATA UPDATE")
    print("=" * 70)

    existing = read_existing_csv()

    scraper = EurojackpotWebScraper()

    # --------------------------------------------------------------
    # Determine years to retrieve.
    # --------------------------------------------------------------

    import datetime

    current_year = datetime.date.today().year

    # Eurojackpot started in 2012.
    first_year = 2012

    downloaded_draws: Dict[str, Dict[str, Any]] = {}

    total_api_draws = 0
    total_valid_draws = 0

    # --------------------------------------------------------------
    # Download year by year.
    # --------------------------------------------------------------

    for year in range(first_year, current_year + 1):
        print(
            f"Fetching Eurojackpot data for {year}..."
        )

        year_draws = scraper.fetch_year_draws(year)

        total_api_draws += len(year_draws)

        valid_for_year = 0

        for draw in year_draws:
            if not validate_draw(draw):
                continue

            downloaded_draws[draw["draw_date"]] = draw
            valid_for_year += 1
            total_valid_draws += 1

        print(
            f"{year}: {valid_for_year} valid draws"
        )

    # --------------------------------------------------------------
    # Critical source check.
    # --------------------------------------------------------------

    if total_api_draws == 0:
        raise RuntimeError(
            "OPAP API returned ZERO draws for the entire historical "
            "update. CSV was not modified."
        )

    if total_valid_draws == 0:
        raise RuntimeError(
            "OPAP API returned data, but ZERO valid Eurojackpot "
            "draws passed validation. CSV was not modified."
        )

    # --------------------------------------------------------------
    # Merge downloaded data with existing data.
    # --------------------------------------------------------------

    before_merge = len(existing)

    for draw_date, draw in downloaded_draws.items():
        existing[draw_date] = draw

    after_merge = len(existing)

    added_or_updated = after_merge - before_merge

    # --------------------------------------------------------------
    # Write final CSV.
    # --------------------------------------------------------------

    write_csv(existing)

    print("=" * 70)
    print("UPDATE COMPLETED")
    print("=" * 70)
    print(
        f"API valid draws downloaded: {total_valid_draws}"
    )
    print(
        f"Existing CSV draws: {before_merge}"
    )
    print(
        f"Final CSV draws: {after_merge}"
    )
    print(
        f"New draw dates added: {max(added_or_updated, 0)}"
    )
    print(
        f"CSV: {CSV_PATH}"
    )
    print("=" * 70)

    return total_valid_draws


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> None:
    """Application entry point."""
    try:
        update_history()

    except Exception as exc:
        print(
            f"ERROR: Historical update failed: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
