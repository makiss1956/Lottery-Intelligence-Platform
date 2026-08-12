-- Lottery Intelligence Platform - Database Schema v0.2

CREATE TABLE IF NOT EXISTS eurojackpot_draws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_number TEXT,
    draw_date DATE NOT NULL UNIQUE,
    n1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL,
    n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL,
    n5 INTEGER NOT NULL,
    e1 INTEGER,
    e2 INTEGER,
    jackpot_euros REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_for_date DATE NOT NULL,
    predicted_primary TEXT NOT NULL,
    predicted_euro TEXT NOT NULL,
    method TEXT DEFAULT 'frequency_7_3',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP,
    actual_draw_number TEXT,
    actual_primary TEXT,
    actual_euro TEXT,
    main_hits INTEGER,
    euro_hits INTEGER,
    matched_main TEXT,
    matched_euro TEXT,
    score_percentage REAL
);

CREATE TABLE IF NOT EXISTS algorithms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS prediction_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    correct_main INTEGER,
    correct_euro INTEGER,
    score REAL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

CREATE INDEX IF NOT EXISTS idx_draws_date ON eurojackpot_draws(draw_date);
CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_for_date);
CREATE INDEX IF NOT EXISTS idx_predictions_evaluated ON predictions(evaluated_at);
