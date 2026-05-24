import sqlite3

conn = sqlite3.connect('slt_mock_data.db')
cursor = conn.cursor()

# Create a table for broadband packages
cursor.execute('''
    CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY,
        name TEXT,
        data_limit_gb INTEGER,
        price_lkr REAL,
        speed_mbps INTEGER
    )
''')

# Insert dummy data
cursor.execute("INSERT INTO packages (name, data_limit_gb, price_lkr, speed_mbps) VALUES ('Fibre Light', 50, 1500, 100)")
cursor.execute("INSERT INTO packages (name, data_limit_gb, price_lkr, speed_mbps) VALUES ('Fibre Plus', 100, 2500, 100)")
conn.commit()