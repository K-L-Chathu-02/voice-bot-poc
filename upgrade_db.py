import sqlite3

conn = sqlite3.connect('slt_mock_data.db')
cursor = conn.cursor()

# 1. Create Customers Table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        phone_number TEXT PRIMARY KEY,
        name TEXT,
        outstanding_bill_lkr REAL,
        remaining_data_gb REAL
    )
''')

# 2. Create Fault Tickets Table (Notice the AUTOINCREMENT ticket_id)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS fault_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT,
        issue_description TEXT,
        status TEXT
    )
''')

# 3. Insert Dummy Customers (Using INSERT OR IGNORE so it won't crash if run twice)
cursor.execute("INSERT OR IGNORE INTO customers VALUES ('0712345678', 'Kamal Perera', 1250.00, 15.5)")
cursor.execute("INSERT OR IGNORE INTO customers VALUES ('0771112222', 'Nimali Silva', 0.00, 45.0)")

conn.commit()
conn.close()
print("Database upgraded with Customers and Fault Tickets!")