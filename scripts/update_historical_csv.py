"""
Batch fetcher for historical EuroJackpot draws.
Updates the CSV file with missing draws from 2020 to present.
Uses euro-jackpot.org archive pages.
"""

import csv
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

CSV_PATH = Path("data/eurojackpot_raw_history.csv")
BASE_URL = "https://www.euro-jackpot.org/en/results-archive-{year}"


def read_existing_dates() -> set:
    """Read all dates already in CSV."""
    if not CSV_PATH.exists():
        return set()
    dates = set()
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            dates.add(row["Date"].strip())
    return dates


def parse_draws_from_html(html: str, year: int) -> List[Dict]:
    """Parse draw results from archive page HTML."""
    draws = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Euro-jackpot.org archive pages list draws in result boxes
    # Each draw typically has a date and ball numbers
    result_boxes = soup.find_all("div", class_=re.compile("result", re.I))
    
    for box in result_boxes:
        # Try to find date
        date_elem = box.find("time") or box.find("span", class_=re.compile("date", re.I))
        if not date_elem:
            continue
        date_text = date_elem.get_text(strip=True)
        
        # Try to find all ball numbers
        balls = box.find_all("span", class_=re.compile("ball", re.I))
        if len(balls) < 7:
            # Some pages use different structure - try generic span with digits
            all_spans = box.find_all("span")
            balls = [s for s in all_spans if s.get_text(strip=True).isdigit()]
        
        nums = []
        for b in balls:
            txt = b.get_text(strip=True)
            if txt.isdigit():
                nums.append(int(txt))
        
        if len(nums) < 7:
            continue
        
        primary = sorted(nums[:5])
        euro = sorted(nums[5:7])
        
        # Parse date - try multiple formats
        draw_date = None
        for fmt in ("%d %B %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                draw_date = datetime.strptime(date_text, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        
        if not draw_date:
            # Try to extract year from context
            try:
                draw_date = datetime.strptime(f"{date_text} {year}", "%d %B %Y").strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        draws.append({
            "Date": draw_date,
            "N1": primary[0], "N2": primary[1], "N3": primary[2],
            "N4": primary[3], "N5": primary[4],
            "E1": euro[0], "E2": euro[1],
            "Jackpot_Euros": 0
        })
    
    return draws


def fetch_year(year: int) -> List[Dict]:
    """Fetch all draws for a specific year."""
    url = BASE_URL.format(year=year)
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=30
        )
        resp.raise_for_status()
        return parse_draws_from_html(resp.text, year)
    except Exception as e:
        print(f"⚠️ Error fetching {year}: {e}")
        return []


def append_to_csv(draws: List[Dict]):
    """Append new draws to CSV file."""
    if not draws:
        return
    fieldnames = ["Date", "N1", "N2", "N3", "N4", "N5", "E1", "E2", "Jackpot_Euros"]
    
    file_exists = CSV_PATH.exists()
    mode = "a" if file_exists else "w"
    
    with open(CSV_PATH, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        if not file_exists:
            writer.writeheader()
        for draw in draws:
            writer.writerow(draw)
    print(f"   💾 Appended {len(draws)} draws to CSV.")


def main():
    print("=" * 60)
    print("📥 EUROJACKPOT HISTORICAL DATA UPDATER")
    print("=" * 60)
    
    existing = read_existing_dates()
    print(f"📊 Existing draws in CSV: {len(existing)}")
    if existing:
        print(f"📅 Last date in CSV: {max(existing)}")
    
    all_new_draws = []
    
    for year in range(2020, 2027):
        print(f"\n🔍 Fetching year {year}...")
        draws = fetch_year(year)
        new_draws = [d for d in draws if d["Date"] not in existing]
        all_new_draws.extend(new_draws)
        print(f"   Found {len(draws)} total, {len(new_draws)} new.")
        time.sleep(2)  # Be polite to the server
    
    if all_new_draws:
        # Sort by date before appending
        all_new_draws.sort(key=lambda x: x["Date"])
        append_to_csv(all_new_draws)
        print(f"\n✅ TOTAL NEW DRAWS ADDED: {len(all_new_draws)}")
        print(f"📅 Date range: {all_new_draws[0]['Date']} to {all_new_draws[-1]['Date']}")
    else:
        print("\nℹ️ No new draws found. CSV is up to date.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
