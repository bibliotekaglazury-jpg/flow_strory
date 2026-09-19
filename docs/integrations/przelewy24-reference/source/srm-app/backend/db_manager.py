import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'saas_radar.db')

def get_db_connection():
    # Adding timeout to avoid hanging if DB is locked by another process
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tables are created only if they don't exist (data preserved)

    # Table for SaaS Users (Authentication)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'client', -- 'admin' or 'client'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Table for SaaS Clients/Shops
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        shop_url TEXT UNIQUE NOT NULL,
        shoper_login TEXT,
        shoper_password TEXT,
        gsc_property_url TEXT NOT NULL,
        gsc_dataset_id TEXT NOT NULL DEFAULT 'searchconsole',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Table for detected 404 errors
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detected_404_errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        impressions INTEGER DEFAULT 0,
        estimated_loss REAL DEFAULT 0.0,
        suggested_redirect_url TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id),
        UNIQUE(client_id, url)
    )
    ''')

    # Table for SaaS Admin - Audit Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        level TEXT DEFAULT 'INFO',
        action TEXT NOT NULL,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')

    # Table for Payments/Subscribers
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'PLN',
        status TEXT DEFAULT 'completed',
        payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')

    # Table for detected 404 errors
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detected_404_errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        impressions INTEGER DEFAULT 0,
        estimated_loss REAL DEFAULT 0.0,
        suggested_redirect_url TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id),
        UNIQUE(client_id, url)
    )
    ''')

    # Table for SaaS Admin - Audit Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        level TEXT DEFAULT 'INFO',
        action TEXT NOT NULL,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')

    # Table for Payments/Subscribers
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'PLN',
        status TEXT DEFAULT 'completed',
        payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    # Table for Redirection History (Tracking Success/Failures)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS redirection_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        target_route TEXT NOT NULL,
        status TEXT NOT NULL, -- 'SUCCESS', 'FAILED', 'ALREADY_EXISTS'
        error_message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
