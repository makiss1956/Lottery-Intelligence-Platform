#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ενημέρωση Ιστορικών Δεδομένων EuroJackpot
Πηγή: Επίσημο αρχείο euro-jackpot.org
"""
import csv
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

# Διαδρομή αρχείου CSV — ευθυγραμμισμένη με τον υπόλοιπο αγωγό
CSV_PATH = Path("data/eurojackpot_history.csv")

# ✅ ΔΙΟΡΘΩΜΕΝΗ διεύθυνση χωρίς κενά/σφάλματα
BASE_URL = "https://www.euro-jackpot.org/en/results/archive/{year}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}


def read_existing_dates() -> set:
    """Ανάγνωση υπαρχόντων ημερομηνιών από CSV."""
    if not CSV_PATH.exists():
        return set()
    dates = set()
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dates.add(row["draw_date"].strip())
    return dates


def parse_date_safely(date_text: str, year: Optional[int] = None) -> Optional[str]:
    """Ασφαλής μετατροπή ημερομηνίας σε μορφή YYYY-MM-DD."""
    date_text = date_text.strip()
    
    # Δοκιμή πολλών μορφών
    formats = ["%d %B %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Αν λείπει το έτος, προσθέτουμε το δοθέν
    if year:
        for fmt in ["%d %B", "%B %d"]:
            try:
                parsed = datetime.strptime(date_text, fmt)
                return f"{year}-{parsed.month:02d}-{parsed.day:02d}"
            except ValueError:
                continue
    
    return None


def parse_draws_from_html(html: str, year: int) -> List[Dict]:
    """Ανάλυση αποτελεσμάτων από HTML σελίδας."""
    draws = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Εύρεση όλων των περιοχών αποτελεσμάτων
    result_boxes = soup.find_all("div", class_=re.compile(r"result|draw|ball", re.I))
    
    if not result_boxes:
        # Εναλλακτική αναζήτηση σε πίνακες
        result_boxes = soup.find_all("tr")
    
    for box in result_boxes:
        # Εύρεση ημερομηνίας
        date_elem = box.find("time") or box.find(class_=re.compile(r"date", re.I)) or box.find("td")
        if not date_elem:
            continue
        
        date_text = date_elem.get_text(strip=True)
        draw_date = parse_date_safely(date_text, year)
        if not draw_date:
            continue
        
        # Εύρεση αριθμών
        balls = box.find_all("span", class_=re.compile(r"ball|num", re.I))
        nums = []
        for b in balls:
            txt = b.get_text(strip=True)
            if txt.isdigit():
                nums.append(int(txt))
        
        # Αν δεν βρέθηκαν με κλάση, δοκιμή όλων των αριθμών
        if len(nums) < 7:
            all_text = box.get_text()
            nums = [int(x) for x in re.findall(r"\b([1-9]|[1-4]\d|50)\b", all_text)]
            nums = nums[:7]
        
        if len(nums) >= 7:
            primary = sorted(nums[:5])
            euro = sorted(nums[5:7])
            
            draws.append({
                "draw_date": draw_date,
                "main_numbers": ",".join(map(str, primary)),
                "extra_numbers": ",".join(map(str, euro))
            })
    
    return draws


def fetch_year(year: int) -> List[Dict]:
    """Λήψη αποτελεσμάτων συγκεκριμένου έτους."""
    url = BASE_URL.format(year=year)
    print(f"   🔗 Συνδέση σε: {url}")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return parse_draws_from_html(resp.text, year)
    except requests.RequestException as e:
        print(f"   ⚠️ Αποτυχία σύνδεσης: {e}")
        return []


def save_csv(draws: List[Dict]):
    """Αποθήκευση στη σωστή μορφή CSV."""
    if not draws:
        return
    
    # Δημιουργία φακέλου αν δεν υπάρχει
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    file_exists = CSV_PATH.exists()
    fieldnames = ["draw_date", "main_numbers", "extra_numbers"]
    
    mode = "a" if file_exists else "w"
    with open(CSV_PATH, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(draws)
    
    print(f"   💾 Αποθηκεύτηκαν {len(draws)} νέες κληρώσεις.")


def main():
    print("=" * 60)
    print("📥 ΕΝΗΜΕΡΩΣΗ ΙΣΤΟΡΙΚΩΝ ΔΕΔΟΜΕΝΩΝ EUROJACKPOT")
    print("=" * 60)
    
    existing = read_existing_dates()
    print(f"📊 Υπάρχουσες κληρώσεις: {len(existing)}")
    if existing:
        print(f"📅 Τελευταία ημερομηνία: {max(existing)}")
    
    # Προσδιορισμός εύρους ετών
    current_year = datetime.now().year
    start_year = 2020
    if existing:
        last_date = max(existing)
        start_year = int(last_date[:4])
    
    all_new_draws = []
    
    for year in range(start_year, current_year + 1):
        print(f"\n🔍 Έλεγχος έτους {year}...")
        draws = fetch_year(year)
        
        if not draws:
            print(f"   ⚠️ Δεν βρέθηκαν αποτελέσματα για {year}")
            time.sleep(2)
            continue
        
        # Φιλτράρισμα νέων κληρώσεων
        new_draws = [d for d in draws if d["draw_date"] not in existing]
        all_new_draws.extend(new_draws)
        print(f"   Βρέθηκαν {len(draws)} συνολικές, {len(new_draws)} νέες.")
        
        time.sleep(3)  # Σεβασμός στον διακομιστή
    
    if all_new_draws:
        all_new_draws.sort(key=lambda x: x["draw_date"])
        save_csv(all_new_draws)
        print(f"\n✅ ΣΥΝΟΛΟ ΝΕΩΝ ΚΛΗΡΩΣΕΩΝ: {len(all_new_draws)}")
        print(f"📅 Εύρος: {all_new_draws[0]['draw_date']} έως {all_new_draws[-1]['draw_date']}")
    else:
        print("\nℹ️ Δεν βρέθηκαν νέες κληρώσεις. Το αρχείο είναι ενημερωμένο.")
    
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
