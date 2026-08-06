## Legal Disclaimer & Purpose

**English:**
This project is an open-source, educational, and research-oriented framework designed strictly for quantitative statistical analysis, historical data research, and mathematical modeling of lottery numbers (Eurojackpot / Tzoker). 

* **No Guarantees or Financial Advice:** This software **does not guarantee, promise, or predict winning outcomes**, profit, or success in any lottery draw. 
* **Independent Random Events:** Lottery draws are purely independent, random stochastic events. Past statistics, frequency patterns, or delay analytics have no mathematical influence on future random outcomes.
* **Entertainment & Research Only:** This platform is intended solely for academic interest, programming practice, data analysis research, and entertainment. 
* **Responsible Gaming:** Users are advised to play responsibly. This project is not affiliated with, endorsed by, or connected to Eurojackpot, OPAP, or any official lottery operator.

---

**Ελληνικά:**
Το παρόν έργο αποτελεί ένα λογισμικό ανοιχτού κώδικα με καθαρά εκπαιδευτικό, ερευνητικό και ψυχαγωγικό χαρακτήρα, το οποίο αναλύει ιστορικά δεδομένα αριθμών (Eurojackpot / Τζόκερ) μέσω μαθηματικών και στατιστικών μοντέλων.

* **Καμία Εγγύηση Επιτυχίας:** Το λογισμικό **δεν παρέχει καμία εγγύηση, υπόσχεση ή πρόβλεψη νίκης** ή κέρδους σε οποιαδήποτε κλήρωση.
* **Καθαρή Τύχη & Ανεξάρτητα Συμβάντα:** Οι κληρώσεις βασίζονται στην απόλυτη τύχη και σε ανεξάρτητα τυχαία συμβάντα. Η στατιστική ανάλυση παρελθόντων αριθμών δεν επηρεάζει ούτε μεταβάλλει τις πιθανότητες μελλοντικών κληρώσεων.
* **Εκπαιδευτική Χρήση:** Η πλατφόρμα προορίζεται αποκλειστικά για την απόκτηση γνώσεων στη μαθηματική ανάλυση δεδομένων, τον προγραμματισμό και την ψυχαγωγία των χρηστών.
* **Υπεύθυνο Παιχνίδι:** Το έργο δεν σχετίζεται, δεν εγκρίνεται και δεν συνδέεται με την εταιρεία Eurojackpot, τον ΟΠΑΠ ή οποιονδήποτε άλλον επίσημο οργανισμό διεξαγωγής παιγνίων.
---

## 📌 Architecture Overview

```text
Lottery-Intelligence-Platform/
├── cli.py                        # Central CLI Entry Point
├── data/                         # SQLite Database Storage
├── database/                     # SQL Schema Definition Files
├── src/
│   ├── analytics/                # Statistical & Prediction Engine
│   │   ├── frequency_analyzer.py # Frequency & Delay Analytics
│   │   ├── predictor.py          # Probability Candidate Selection (7+3 window)
│   │   └── backtester.py         # Evaluation & Backtesting Engine
│   ├── core/                     # Logging & Core Utilities
│   ├── database/                 # SQLite Database Manager
│   ├── importers/                # Web Scrapers & API Data Fetchers
│   ├── utils/                    # Data Validation & Sanitization
│   └── main.py                   # Central Orchestrator Pipeline
└── tests/                        # Automated Unit Tests (pytest)
