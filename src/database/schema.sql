-- Lottery Intelligence Platform
-- Database Schema v0.1

CREATE TABLE draws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_date DATE NOT NULL,
    lottery TEXT NOT NULL,
    n1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL,
    n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL,
    n5 INTEGER NOT NULL,
    e1 INTEGER,
    e2 INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE algorithms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    active INTEGER DEFAULT 1
);

CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER,
    prediction_date DATE,
    n1 INTEGER,
    n2 INTEGER,
    n3 INTEGER,
    n4 INTEGER,
    n5 INTEGER,
    e1 INTEGER,
    e2 INTEGER,
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id)
);

CREATE TABLE prediction_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    correct_main INTEGER,
    correct_euro INTEGER,
    score REAL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);
