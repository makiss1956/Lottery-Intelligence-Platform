#!/usr/bin/env python3
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

CSV_PATH = Path("data/eurojackpot_raw_history.csv")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_balls(cell_text):
    text = cell_text.strip().upper().replace("-", "")
    digits = re.findall(r"\d{1,2}", text)
    if len(digits) >= 7:
        return digits[:5], digits[5:7]
    raise ValueError(f"Cannot parse balls from: '{cell_text}'")

def parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
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
    with CSV_PATH.open("r", encoding="utf-8") as f:
        # Ανάγνωση της πρώτης γραμμής για εντοπισμό διαχωριστικού
        first_line = f.readline()
        delimiter = ";" if ";" in first_line else ","
        f.seek(0)
       
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader, None)
       
        for row in reader:
            if not row or len(row) < 8:
                continue
            d_str = row[0].strip()
            if d_str:
                seen_dates.add(d_str)
                # Διατηρούμε τη δομή 9 στηλών
                jackpot = row[8].strip() if len(row) > 8 else "0.00"
                rows.append({
                    "Date": d_str,
                    "N1": row[1].strip(),
                    "N2": row[2].strip(),
                    "N3": row[3].strip(),
                    "N4": row[4].strip(),
                    "N5": row[5].strip(),
                    "E1": row[6].strip(),
                    "E2": row[7].strip(),
                    "Jackpot_Euros": jackpot
                })
    return rows, seen_dates

def fetch_year(year):
    url = f"https://www.beatlottery.co.uk/eurojackpot/draw-history/{year}"
    print(f"Fetching {url} ...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
       
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        rows = table.find_all("tr")
        draws = []

        for tr in rows[1:]:
            tds = tr.find_all(["td", "th"])
            if len(tds) < 3:
                continue

            try:
                texts = [td.get_text(strip=True) for td in tds]
                date_str = texts[0]
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
            except Exception:
                continue

        return draws
    except Exception as e:
        print(f"Error fetching year {year}: {e}")
        return []

def main():
    print("=" * 60)
    print("EUROJACKPOT COMPLETE HISTORICAL DATA UPDATER (2012-2026)")
    print("=" * 60)

    existing_rows, seen_dates = load_existing()
    print(f"Existing draws recovered in CSV: {len(existing_rows)}")

    all_fetched = []
    # Σαρώνουμε όλα τα έτη από το 2012 έως το 2026
    for year in range(2012, 2027):
        year_draws = fetch_year(year)
        all_fetched.extend(year_draws)

    new_draws = [d for d in all_fetched if d["Date"] not in seen_dates]

    print(f"\nTotal fetched from source (2012-2026): {len(all_fetched)}")
    print(f"New draws to add: {len(new_draws)}")

    # Συγχώνευση παλιών και νέων χωρίς διπλότυπα
    merged_dict = {r["Date"]: r for r in existing_rows}
    for nd in new_draws:
        merged_dict[nd["Date"]] = nd

    all_rows = list(merged_dict.values())
    all_rows.sort(key=lambda r: r["Date"])

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
   
    fieldnames = ["Date", "N1", "N2", "N3", "N4", "N5", "E1", "E2", "Jackpot_Euros"]
   
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSUCCESS: Saved {len(all_rows)} total historical draws to {CSV_PATH}")

if __name__ == "__main__":
    main()
