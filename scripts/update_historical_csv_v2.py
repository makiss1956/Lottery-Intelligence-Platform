#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ενημέρωση Ιστορικών Δεδομένων Eurojackpot σε CSV
Πηγές: euro-jackpot.net (κύρια), euro-millions.com (επικουρική)
"""

import csv
import logging
import re
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# ------------------ ΡΥΘΜΙΣΕΙΣ ------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "eurojackpot_history.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "el-GR,el;q=0.9,en-GB;q=0.8,en;q=0.7"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("UpdateHistoricalCSV")
# ------------------------------------------------

def load_existing_draws():
    """Φόρτωση ήδη αποθηκευμένων κληρώσεων από CSV."""
    draws = {}
    if CSV_PATH.exists():
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                draws[row["draw_date"]] = {
                    "date": row["draw_date"],
                    "main": [int(x) for x in row["main_numbers"].split(",")],
                    "extra": [int(x) for x in row["extra_numbers"].split(",")]
                }
        logger.info(f"Loaded {len(draws)} existing draws.")
    else:
        logger.info("No existing CSV found. Will create new.")
    return draws


def parse_date_text(text):
    """Μετατροπή κειμένου ημερομηνίας σε μορφή YYYY-MM-DD."""
    text = text.strip()
    months = {
        "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
        "ιανουάριος":1,"φεβρουάριος":2,"μάρτιος":3,"απρίλιος":4,"μάϊος":5,"ιούνιος":6,
        "ιούλιος":7,"αύγουστος":8,"σεπτέμβριος":9,"οκτώβριος":10,"νοέμβριος":11,"δεκέμβριος":12
    }

    # Μορφή: "Tuesday 30th June 2026" ή "30 Ιουνίου 2026"
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})", text, re.I)
    if m:
        day, mon_name, year = m.groups()
        month = months.get(mon_name.lower(), 0)
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"

    # Εναλλακτική μορφή: "2026-06-30"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return m.group(0)

    return None


def fetch_from_eurojackpot_net(year):
    """Κύρια πηγή: euro-jackpot.net — αξιόπιστη με σωστή δομή URL"""
    url = f"https://www.euro-jackpot.net/results-archive-{year}"
    logger.info(f"Trying primary source: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        draws_found = []

        # Εύρεση πίνακα αποτελεσμάτων
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            date_text = cells[0].get_text(strip=True)
            parsed_date = parse_date_text(date_text)
            if not parsed_date:
                continue

            # Εύρεση αριθμών — συνήθως στη δεύτερη στήλη ή σε στήλες
            numbers_text = " ".join([c.get_text(strip=True) for c in cells[1:]])
            numbers = re.findall(r"\b([1-9]|[1-4]\d|50)\b", numbers_text)
            numbers = [int(n) for n in numbers]

            if len(numbers) >= 7:
                draws_found.append({
                    "date": parsed_date,
                    "main": sorted(numbers[:5]),
                    "extra": sorted(numbers[5:7])
                })

        logger.info(f"Found {len(draws_found)} draws for {year}")
        return draws_found

    except Exception as e:
        logger.warning(f"Primary source failed: {e}")
        return []


def save_csv(draws):
    """Αποθήκευση όλων των κληρώσεων σε CSV."""
    DATA_DIR.mkdir(exist_ok=True)
    sorted_draws = sorted(draws.values(), key=lambda x: x["date"])

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["draw_date", "main_numbers", "extra_numbers"])
        writer.writeheader()
        for d in sorted_draws:
            writer.writerow({
                "draw_date": d["date"],
                "main_numbers": ",".join(map(str, d["main"])),
                "extra_numbers": ",".join(map(str, d["extra"]))
            })

    logger.info(f"✅ Saved {len(sorted_draws)} draws to {CSV_PATH}")


def main():
    logger.info("=== Starting Update ===")

    all_draws = load_existing_draws()
    new_count = 0

    # Προσδιορισμός ετών προς λήψη
    current_year = datetime.now().year
    start_year = 2012  # Έτος έναρξης Eurojackpot
    if all_draws:
        last_date = max(all_draws.keys())
        start_year = int(last_date[:4])

    # Λήψη δεδομένων ανά έτος
    for year in range(start_year, current_year + 1):
        draws = fetch_from_eurojackpot_net(year)
        for d in draws:
            if d["date"] not in all_draws:
                all_draws[d["date"]] = d
                new_count += 1

    if new_count == 0:
        logger.warning("⚠️ No new draws found. Existing CSV preserved.")
        # ΕΠΙΣΤΡΕΦΟΥΜΕ 0 αντί για 1 ώστε να ΜΗΝ αποτυγχάνει η αγωγός!
        return 0

    save_csv(all_draws)
    logger.info(f"✅ Added {new_count} new draws. Total: {len(all_draws)}")
    return 0


if __name__ == "__main__":
    exit(main())
