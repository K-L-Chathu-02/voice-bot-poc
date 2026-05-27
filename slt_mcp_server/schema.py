import sqlite3

DDL = [
    """
    CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        data_limit_gb INTEGER NOT NULL,
        price_lkr REAL NOT NULL,
        speed_mbps INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customers (
        phone_number TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        outstanding_bill_lkr REAL NOT NULL DEFAULT 0,
        remaining_data_gb REAL NOT NULL DEFAULT 0,
        current_package_id INTEGER REFERENCES packages(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT NOT NULL REFERENCES customers(phone_number),
        amount_lkr REAL NOT NULL,
        method TEXT NOT NULL,
        reference TEXT,
        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS addons (
        addon_code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        data_gb REAL NOT NULL,
        price_lkr REAL NOT NULL,
        validity_days INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS outages (
        outage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        district TEXT NOT NULL,
        area TEXT,
        service_type TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TIMESTAMP,
        eta_resolution TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fault_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT NOT NULL,
        issue_description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

SEED_PACKAGES = [
    (1, "Fibre Light", 50, 1500.0, 50),
    (2, "Fibre Plus", 100, 2500.0, 100),
    (3, "Fibre Max", 300, 4500.0, 300),
]

SEED_CUSTOMERS = [
    ("0712345678", "Kamal Perera", 1250.0, 15.5, 1),
    ("0771112222", "Nimali Silva", 0.0, 45.0, 2),
]

SEED_PAYMENTS = [
    ("0712345678", 1500.0, "card", "****4421", "2026-04-15 10:14:00"),
    ("0712345678", 500.0, "reload_card", "RC8821", "2026-05-02 18:02:00"),
    ("0771112222", 2500.0, "ezcash", "EZ9911", "2026-04-22 09:30:00"),
    ("0771112222", 2500.0, "bank_transfer", "BT5512", "2026-05-22 09:30:00"),
]

SEED_ADDONS = [
    ("DATA5", "5GB Daily", 5.0, 150.0, 1),
    ("DATA20", "20GB Weekly", 20.0, 500.0, 7),
    ("NIGHT50", "Night 50GB", 50.0, 800.0, 30),
]

SEED_OUTAGES = [
    ("Colombo", "Nugegoda", "fibre", "repair_in_progress",
     "2026-05-27 06:00:00", "2026-05-27 14:00:00"),
    ("Kandy", None, "mobile_data", "investigating",
     "2026-05-27 08:30:00", None),
    ("Jaffna", None, "fibre", "resolved",
     "2026-05-26 22:00:00", "2026-05-27 02:00:00"),
]


def apply(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    for stmt in DDL:
        cur.execute(stmt)

    cur.executemany(
        "INSERT OR IGNORE INTO packages (id, name, data_limit_gb, price_lkr, speed_mbps) "
        "VALUES (?, ?, ?, ?, ?)",
        SEED_PACKAGES,
    )
    cur.executemany(
        "INSERT OR IGNORE INTO customers "
        "(phone_number, name, outstanding_bill_lkr, remaining_data_gb, current_package_id) "
        "VALUES (?, ?, ?, ?, ?)",
        SEED_CUSTOMERS,
    )
    cur.executemany(
        "INSERT OR IGNORE INTO addons (addon_code, name, data_gb, price_lkr, validity_days) "
        "VALUES (?, ?, ?, ?, ?)",
        SEED_ADDONS,
    )

    cur.execute("SELECT COUNT(*) FROM payments")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO payments (phone_number, amount_lkr, method, reference, paid_at) "
            "VALUES (?, ?, ?, ?, ?)",
            SEED_PAYMENTS,
        )

    cur.execute("SELECT COUNT(*) FROM outages")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO outages (district, area, service_type, status, started_at, eta_resolution) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            SEED_OUTAGES,
        )

    conn.commit()
    cur.close()
