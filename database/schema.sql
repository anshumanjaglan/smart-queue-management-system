-- Schema for Smart Queue Management System

CREATE TABLE IF NOT EXISTS outlets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    service_type TEXT NOT NULL,
    counter_number TEXT DEFAULT 'Counter 1',
    avg_service_time_mins REAL DEFAULT 3.0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outlet_id INTEGER NOT NULL,
    token_number TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    notification_pref TEXT DEFAULT 'both', -- 'sms', 'call', 'both'
    status TEXT DEFAULT 'WAITING',         -- 'WAITING', 'CALLED', 'COMPLETED', 'CANCELLED', 'NO_SHOW'
    notes TEXT DEFAULT '',
    queue_position INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    called_at TIMESTAMP,
    completed_at TIMESTAMP,
    wait_duration_secs INTEGER DEFAULT 0,
    service_duration_secs INTEGER DEFAULT 0,
    estimated_wait_mins REAL DEFAULT 0,
    FOREIGN KEY (outlet_id) REFERENCES outlets (id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER NOT NULL,
    customer_phone TEXT NOT NULL,
    type TEXT NOT NULL,                    -- 'SMS' or 'CALL'
    status TEXT NOT NULL,                  -- 'SENT', 'SIMULATED', 'FAILED'
    message_body TEXT NOT NULL,
    provider_sid TEXT DEFAULT '',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (token_id) REFERENCES tokens (id)
);

CREATE INDEX IF NOT EXISTS idx_tokens_outlet_status ON tokens (outlet_id, status);
CREATE INDEX IF NOT EXISTS idx_tokens_joined_at ON tokens (joined_at);
CREATE INDEX IF NOT EXISTS idx_tokens_status ON tokens (status);
