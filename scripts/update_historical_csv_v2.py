#!/usr/bin/env python3
"""
Eurojackpot Historical Data Updater — Alternative Source (beatlottery.co.uk)
Replaces broken eurojackpot.org scraper. Fetches complete draw history
from 23 March 2012 to present.

Usage:
    python scripts/update_historical_csv_v2.py

Requirements:
    pip install requests beautifulsoup4
"""

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── CONFIG ──────────────────────────────────────────────────────────
CSV_PATH = Path("data/eurojackpot_raw_history.csv")
SOURCE_URL = "https://www.beatlottery.co.uk/eurojackpot/draw-history"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── HELPERS ─────────────────────────────────────────────────────────
def parse_balls(cell_text: str):
    """
    beatlottery format: 0411121630EURO NUMBERS0809
    -> main [04,11,12,16,30], euro [08,09]
    """
    text = cell_text.strip().upper().replace(" ", "")
    parts = re.split(r"EURO\s*NUMBERS", text, flags=re.IGNORECASE)
    if len(parts) != 2:
        # fallback: extract all numbers
        digits = re.findall(r"\d{1,2}", text)
        if len(digits) >= 7:
            return digits[:5], digits[5:7]
        raise ValueError(f"Cannot parse balls from: {cell_text!r}")

    main = re.findall(r"\d{1,2}", parts[0])
    euro = re.findall(r"\d{1,2}", parts[1])

    if len(main) < 5 or len(euro) < 2:
        raise ValueError(f"Incomplete ball data: {cell_text!r}")

    return main[:5], euro[:2]


def parse_date(date_str: str):
    """Convert '11 Aug 2026' or '11/08/2026' to ISO YYYY-MM-DD."""
    date_str = date_str.strip()
    for fmt in ("%d %b %Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str!r}")


# ── LOAD EXISTING CSV ───────────────────────────────────────────────
def load_existing():
    if not CSV_PATH.exists():
        return [], set()

    rows = []
    seen_dates = set()
    with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            seen_dates.add(row.get("Date", "").strip())
    return rows, seen_dates


# ── FETCH & PARSE ───────────────────────────────────────────────────
def fetch_draws():
    print(f"🔍 Fetching {SOURCE_URL} ...")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        raise RuntimeError("No table found on page — site structure may have changed.")

    rows = table.find_all("tr")
    draws = []
    skipped = 0

    for tr in rows[1:]:  # skip header
        tds = tr.find_all(["td", "th"])
        if len(tds) < 4:
            continue

        try:
            date_str   = tds[0].get_text(strip=True)
            day_str    = tds[1].get_text(strip=True)
            balls_cell = tds[2].get_text(strip=True)

            draw_date = parse_date(date_str)
            main, euro = parse_balls(balls_cell)

            draws.append({
                "Date": draw_date.isoformat(),
                "Day": day_str,
                "N1": main[0],
                "N2": main[1],
                "N3": main[2],
                "N4": main[3],
                "N5": main[4],
                "E1": euro[0],
                "E2": euro[1],
            })
        except Exception as e:
            skipped += 1
            if skipped <= 3:
                print(f"   ⚠️  Skipping row: {e}")
            continue

    if skipped > 3:
        print(f"   ⚠️  ... and {skipped - 3} more skipped rows")

    draws.sort(key=lambda d: d["Date"])
    return draws


# ── MAIN ────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("📥 EUROJACKPOT HISTORICAL DATA UPDATER (beatlottery.co.uk)")
    print("=" * 60)

    existing_rows, seen_dates = load_existing()
    print(f"📊 Existing draws in CSV: {len(existing_rows)}")
    if existing_rows:
        last = max(existing_rows, key=lambda r: r.get("Date", ""))
        print(f"📅 Last date in CSV: {last.get('Date', 'N/A')}")

    try:
        fetched = fetch_draws()
    except Exception as e:
        print(f"\n❌ Error fetching data: {e}")
        sys.exit(1)

    new_draws = [d for d in fetched if d["Date"] not in seen_dates]

    print(f"\n📥 Fetched {len(fetched)} total draws from source.")
    print(f"✨ New draws to add: {len(new_draws)}")

    if not new_draws:
        print("ℹ️  No new draws found. CSV is up to date.")
        print("=" * 60)
        return

    # Merge and write
    all_rows = existing_rows + new_draws
    all_rows.sort(key=lambda r: r.get("Date", ""))

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["Date", "Day", "N1", "N2", "N3", "N4", "N5", "E1", "E2"]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n💾 Saved {len(all_rows)} total draws to {CSV_PATH}")
    print(f"📈 Added {len(new_draws)} new draws.")
    print("=" * 60)


if __name__ == "__main__":
    main()
