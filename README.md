# 🎯 Lottery Intelligence Platform

An open-source, modular Python framework for statistical and chaos theory analysis of lottery data (Eurojackpot). Designed for quantitative research, frequency/delay analytics, model evaluation via backtesting, and probability prediction.

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
