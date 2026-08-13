#!/usr/bin/env python3
import csv
import re
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

CSV_PATH = Path("data/eurojackpot_raw_history.csv")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MONTHS_GR = {
    "ιανουαριου": 1, "φεβρουαριου": 2, "μαρτιου": 3, "απριλιου": 4,
    "μαϊου": 5, "μαιου": 6, "ιουνιου": 7, "ιουλιου": 8,
    "αυγουστου": 9, "σεπτεμβριου": 10, "οκτωβριου": 11, "νοεμβριου": 12, "δεκεμβριου": 13
}
# Standard Greek month names mapping
GREEK_MONTHS = {
    "ιανουαριου": 1, "φεβρουαριου": 2, "μαρτιου": 3, "απριλιου": 4,
    "μαιου": 5, "μαϊου": 5, "ιουνιου": 6, "ιουλιου": 7,
    "αυγουστου": 8, "σεπτεμβριου": 9, "οκτωβριου": 10, "νοεμβριου": 11, "δεκεμβριου": 12
}

def parse_greek_date(date_str):
    # e.g. "28 Δεκεμβρίου 2012"
    clean_str = date_str.strip().lower()
    parts = clean_str.split()
    if len(parts) >= 3:
        day = int(parts[0])
        month_str = parts[1]
        year = int(parts[2])
        month = GREEK_MONTHS.get(month_str, 1)
        return datetime(year, month, day).date()
    raise ValueError(f"Cannot parse date: {date_str}")

def load_existing():
    if not CSV_PATH.exists():
        return [], set()

    rows = []
    seen_dates = set()
    with CSV_PATH.open("r", encoding="utf-8") as f:
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

def fetch_jackpot_stats_year(year):
    url = f"https://jackpot-stats.com/el/eurojackpot/archive/{year}"
    print(f"Fetching {url} ...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"  Status code: {resp.status_code}")
            return []
       
        soup = BeautifulSoup(resp.text, "html.parser")
        draws = []

        # Find all draw items or links containing /results/
        links = soup.find_all("a", href=re.compile(r"/el/eurojackpot/results/\d{4}-\d{2}-\d{2}"))
       
        for link in links:
            try:
                # Get date from href or text
                href = link.get("href", "")
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", href)
                if date_match:
                    iso_date = date_match.group(0)
                else:
                    continue

                # Find parent or container to get numbers
                parent = link.find_parent(["div", "li", "tr"]) or link
                numbers = [span.get_text(strip=True) for span in parent.find_all(["span", "div"]) if span.get_text(strip=True).isdigit()]
               
                # We need 7 numbers (5 main + 2 euro)
                if len(numbers) >= 7:
                    main_nums = numbers[:5]
                    euro_nums = numbers[5:7]
                   
                    draws.append({
                        "Date": iso_date,
                        "N1": str(int(main_nums[0])),
                        "N2": str(int(main_nums[1])),
                        "N3": str(int(main_nums[2])),
                        "N4": str(int(main_nums[3])),
                        "N5": str(int(main_nums[4])),
                        "E1": str(int(euro_nums[0])),
                        "E2": str(int(euro_nums[1])),
                        "Jackpot_Euros": "0.00"
                    })
            except Exception:
                continue

        # Deduplicate fetched draws for this year
        unique_draws = {d["Date"]: d for d in draws}
        return list(unique_draws.values())

    except Exception as e:
        print(f"Error fetching year {year}: {e}")
        return []

def main():
    print("=" * 60)
    print("EUROJACKPOT ARCHIVE SCRAPER (jackpot-stats.com 2012-2026)")
    print("=" * 60)

    existing_rows, seen_dates = load_existing()
    print(f"Existing draws in CSV: {len(existing_rows)}")

    all_fetched = []
    for year in range(2012, 2027):
        year_draws = fetch_jackpot_stats_year(year)
        print(f"  Found {len(year_draws)} draws for year {year}")
        all_fetched.extend(year_draws)

    merged_dict = {r["Date"]: r for r in existing_rows}
    new_count = 0
    for nd in all_fetched:
        if nd["Date"] not in merged_dict:
            new_count += 1
        merged_dict[nd["Date"]] = nd

    all_rows = list(merged_dict.values())
    all_rows.sort(key=lambda r: r["Date"])

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["Date", "N1", "N2", "N3", "N4", "N5", "E1", "E2", "Jackpot_Euros"]
   
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(all_rows)

    print("=" * 60)
    print(f"SUCCESS: Added {new_count} new draws.")
    print(f"Total historical draws now in CSV: {len(all_rows)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
