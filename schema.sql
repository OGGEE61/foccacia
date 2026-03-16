CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT,
    product_name TEXT,
    vendor TEXT,
    price REAL,
    currency TEXT,
    timestamp TEXT
);
