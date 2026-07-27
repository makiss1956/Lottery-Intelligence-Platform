-- 1. Πίνακας Κληρώσεων
CREATE TABLE IF NOT EXISTS draws (
    draw_id INTEGER PRIMARY KEY,
    draw_date DATE NOT NULL,
    game_type TEXT NOT NULL
);

-- 2. Αριθμοί Κληρώσεων
CREATE TABLE IF NOT EXISTS draw_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_id INTEGER,
    number INTEGER NOT NULL,
    FOREIGN KEY (draw_id) REFERENCES draws(draw_id)
);

-- 3. Αριθμοί Eurojackpot / Joker (Extra numbers)
CREATE TABLE IF NOT EXISTS euro_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_id INTEGER,
    number INTEGER NOT NULL,
    FOREIGN KEY (draw_id) REFERENCES draws(draw_id)
);

-- 4. Αλγόριθμοι
CREATE TABLE IF NOT EXISTS algorithms (
    algorithm_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

-- 5. Προβλέψεις
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(algorithm_id)
);

-- 6. Σύνολα Προβλέψεων
CREATE TABLE IF NOT EXISTS prediction_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    predicted_number INTEGER NOT NULL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
);

-- 7. Αποτελέσματα Αλγορίθμων
CREATE TABLE IF NOT EXISTS algorithm_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    draw_id INTEGER,
    matches_count INTEGER,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id),
    FOREIGN KEY (draw_id) REFERENCES draws(draw_id)
);

-- 8. Στατιστικά
CREATE TABLE IF NOT EXISTS statistics (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_name TEXT NOT NULL,
    stat_value REAL NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. Cache Συχνότητας (Frequency Cache)
CREATE TABLE IF NOT EXISTS frequency_cache (
    number INTEGER PRIMARY KEY,
    frequency INTEGER NOT NULL,
    last_drawn_date DATE
);

-- 10. Cache Ζευγαριών (Pair Cache)
CREATE TABLE IF NOT EXISTS pair_cache (
    num1 INTEGER NOT NULL,
    num2 INTEGER NOT NULL,
    frequency INTEGER NOT NULL,
    PRIMARY KEY (num1, num2)
);

-- 11. Cache Τριάδων (Triplet Cache)
CREATE TABLE IF NOT EXISTS triplet_cache (
    num1 INTEGER NOT NULL,
    num2 INTEGER NOT NULL,
    num3 INTEGER NOT NULL,
    frequency INTEGER NOT NULL,
    PRIMARY KEY (num1, num2, num3)
);

-- 12. Χρήστες
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    role TEXT DEFAULT 'user'
);

-- 13. Ρυθμίσεις
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 14. Logs
CREATE TABLE IF NOT EXISTS logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

 
