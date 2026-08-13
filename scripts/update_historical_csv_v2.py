#!/usr/bin/env python3
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

CSV_PATH = Path("data/eurojackpot_raw_history.csv")
SOURCE_URL = "https://www.beatlottery.co.uk/eurojackpot/draw-history"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_balls(cell_text):
    text = cell_text.strip().upper().replace("-", "")
    parts = re.split(r"EURO\s*NUMBERS", text, flags=re.IGNORECASE)
    if len(parts) != 2:
        digits = re.findall(r"\d{1,2}", text)
        if len(digits) >= 7:
            return digits[:5], digits[5:7]
        raise ValueError(f"Cannot parse balls from: '{cell_text}'")

    main = re.findall(r"\d{1,2}", parts[0])
    euro = re.findall(r"\d{1,2}", parts[1])

    if len(main) < 5 or len(euro) < 2:
        raise ValueError(f"Incomplete ball data: '{cell_text}'")

    return main[:5], euro[:2]

def parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ("%d %b %Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: '{date_str}'")

def load_existing():
    if not CSV_PATH.exists():
        return [], set()

    rows = []
    seen_dates = set()
    # Διαβάζουμε με delimiter ';' επειδή το αρχείο είναι semicolon-separated
    with CSV_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rows.append(row)
            if row.get("Date"):
                seen_dates.add(row["Date"].strip())
    return rows, seen_dates

def fetch_draws():
    print(f"Fetching {SOURCE_URL} ...")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        raise RuntimeError("No table found on page")

    rows = table.find_all("tr")
    draws = []
    skipped = 0

    for tr in rows[1:]:
        tds = tr.find_all(["td", "th"])
        if len(tds) < 3:
            continue

        try:
            texts = [td.get_text(strip=True) for td in tds]
            date_str = texts[0]

            if texts[1] in ["Tue", "Fri", "Tue,", "Fri,"]:
                balls_cell = " ".join(texts[2:])
            else:
                balls_cell = " ".join(texts[1:])

            draw_date = parse_date(date_str)
            main_nums, euro_nums = parse_balls(balls_cell)

            draws.append({
                "Date": draw_date.isoformat(),
                "N1": main_nums[0],
                "N2": main_nums[1],
                "N3": main_nums[2],
                "N4": main_nums[3],
                "N5": main_nums[4],
                "E1": euro_nums[0],
                "E2": euro_nums[1],
                "Jackpot_Euros": "0.00"
            })
        except Exception as e:
            skipped += 1
            if skipped <= 3:
                print(f"Skipping row: {e}")
            continue

    return draws

def main():
    print("=" * 60)
    print("EUROJACKPOT HISTORICAL DATA UPDATER")
    print("=" * 60)

    existing_rows, seen_dates = load_existing()
    print(f"Existing draws in CSV: {len(existing_rows)}")

    fetched = fetch_draws()
    new_draws = [d for d in fetched if d["Date"] not in seen_dates]

    print(f"\nFetched {len(fetched)} total draws from source.")
    print(f"New draws to add: {len(new_draws)}")

    if not new_draws:
        print("No new draws found. CSV is up to date.")
        return

    all_rows = existing_rows + new_draws
    all_rows.sort(key=lambda r: r.get("Date", ""))

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
   
    # Τα πεδία ταιριάζουν ακριβώς με την κεφαλίδα του υφιστάμενου CSV
    fieldnames = ["Date", "N1", "N2", "N3", "N4", "N5", "E1", "E2", "Jackpot_Euros"]
   
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} total draws to {CSV_PATH}")
    print(f"Added {len(new_draws)} new draws.")

if __name__ == "__main__":
    main()
