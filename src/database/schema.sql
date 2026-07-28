-- 1. Πίνακας Βασικών Στοιχειών Κληρώσεων
CREATE TABLE IF NOT EXISTS draws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_name TEXT NOT NULL,          -- π.χ. 'JOKER', 'EUROJACKPOT'
    draw_id INTEGER NOT NULL,         -- Αριθμός κλήρωσης
    draw_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_name, draw_id)
);

-- 2. Πίνακας Αριθμών Κλήρωσης
CREATE TABLE IF NOT EXISTS draw_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_id INTEGER NOT NULL,
    number_value INTEGER NOT NULL,
    is_powerball BOOLEAN DEFAULT 0,   -- 1 για Τζόκερ/Extra number, 0 για βασικό
    FOREIGN KEY (draw_id) REFERENCES draws(id) ON DELETE CASCADE
);

-- 3. Πίνακας Αλγορίθμων
CREATE TABLE IF NOT EXISTS algorithms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,        -- π.χ. 'Frequency_Analysis', 'Markov_Chain'
    description TEXT,
    version TEXT DEFAULT '1.0'
);

-- 4. Πίνακας Προβλέψεων
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER NOT NULL,
    target_draw_id INTEGER,
    predicted_numbers TEXT NOT NULL,  -- π.χ. '3,12,25,33,42'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id)
);

-- 5. Πίνακας Αποτελεσμάτων / Αξιολόγησης
CREATE TABLE IF NOT EXISTS prediction_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL,
    matches_count INTEGER NOT NULL,   -- Πόσες επιτυχίες είχαμε
    score REAL,                       -- Βαθμολογία απόδοσης
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

-- 6. Πίνακας Cache Στατιστικών (για γρήγορη εκτέλεση)
CREATE TABLE IF NOT EXISTS statistics_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,        -- π.χ. 'hot_numbers', 'due_numbers'
    data_json TEXT NOT NULL,          -- Αποτελέσματα σε μορφή JSON
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Πίνακας Ρυθμίσεων
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Ευρετήρια (Indexes) για ταχύτητα αναζήτησης
CREATE INDEX IF NOT EXISTS idx_draws_date ON draws(draw_date);
CREATE INDEX IF NOT EXISTS idx_draw_numbers_lookup ON draw_numbers(draw_id, number_value);

