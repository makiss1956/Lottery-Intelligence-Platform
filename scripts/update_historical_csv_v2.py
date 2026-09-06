#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ενημέρωση Ιστορικών Δεδομένων Eurojackpot σε CSV
Πηγή: Επίσημο αρχείο Eurojackpot + εναλλακτικές πηγές
"""

import csv
import json
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

# Πηγές δεδομένων (σε σειρά προτίμησης)
SOURCES = [
    {
        "name": "Eurojackpot Official Archive",
        "url": "https://eurojackpot.de/en/results/archive",
        "type": "html"
    },
    {
        "name": "Euro-Millions.com Archive",
        "url": "https://www.euro-millions.com/eurojackpot/results",
        "type": "html"
    }
]

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


def fetch_from_alternative_source(year):
    """Λήψη δεδομένων από εναλλακτική πηγή."""
    url = f"https://www.euro-millions.com/eurojackpot/results/{year}"
    logger.info(f"Trying: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        draws_found = []

        # Αναζήτηση με ευέλικτους επιλογείς
        result_blocks = soup.select(".results-listing__item, .draw-result, .result-item")
        if not result_blocks:
            result_blocks = soup.find_all("div", class_=re.compile(r"result|draw"))

        for block in result_blocks:
            try:
                # Ημερομηνία
                date_tag = block.find("a", href=re.compile(r"/results/")) or block.find("time") or block.find("strong")
                if not date_tag:
                    continue

                date_text = date_tag.get_text(strip=True)
                # Μετατροπή σε μορφή YYYY-MM-DD
                parsed = parse_date(date_text, year)
                if not parsed:
                    continue

                # Αριθμοί — αναζήτηση με ευέλικτο τρόπο
                number_spans = block.select(".ball, .num, .number, .result-ball")
                if len(number_spans) >= 7:
                    numbers = [int(s.get_text(strip=True)) for s in number_spans[:7] if s.get_text(strip=True).isdigit()]
                    if len(numbers) == 7:
                        draws_found.append({
                            "date": parsed,
                            "main": numbers[:5],
                            "extra": numbers[5:]
                        })
            except Exception as e:
                logger.debug(f"Parse error in block: {e}")
                continue

        logger.info(f"Found {len(draws_found)} draws for {year}")
        return draws_found

    except Exception as e:
        logger.error(f"Failed to fetch {year}: {e}")
        return []


def parse_date(text, default_year):
    """Μετατροπή κειμένου ημερομηνίας σε YYYY-MM-DD."""
    text = re.sub(r"\s+", " ", text.strip())
    patterns = [
        r"(\d{1,2})\s+(\w+)\s+(\d{4})",
        r"(\w+)\s+(\d{1,2}),?\s+(\d{4})",
    ]

    months = {
        "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12
    }

    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            a, b, c = m.groups()
            try:
                day = int(a) if a.isdigit() else int(b)
                mon_name = b if not a.isdigit() else a
                year = int(c) if c.isdigit() else default_year
                mon = months.get(mon_name.lower(), 1)
                return f"{year}-{mon:02d}-{day:02d}"
            except:
                continue
    return None


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

    logger.info(f"Saved {len(sorted_draws)} draws to {CSV_PATH}")


def main():
    logger.info("=== Starting Update ===")

    # Φόρτωση υπαρχόντων
    all_draws = load_existing_draws()

    # Εύρεση τελευταίας ημερομηνίας
    last_year = 2025
    if all_draws:
        last_date = max(all_draws.keys())
        last_year = int(last_date[:4])

    # Λήψη για το τρέχον έτος
    current_year = datetime.now().year
    new_count = 0

    for year in [2025, current_year]:
        draws = fetch_from_alternative_source(year)
        for d in draws:
            if d["date"] not in all_draws:
                all_draws[d["date"]] = d
                new_count += 1

    if new_count == 0:
        logger.warning("⚠️ No new draws found. CSV NOT modified.")
        return 1

    save_csv(all_draws)
    logger.info(f"✅ Added {new_count} new draws. Total: {len(all_draws)}")
    return 0


if __name__ == "__main__":
    exit(main())
