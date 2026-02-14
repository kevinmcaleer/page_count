import sqlite3
import json
import sys
import os

DB_PATH = './data/visits.db'

def import_historic(json_path):
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
    records = []
    with open(json_path, 'r') as f:
        first_line = f.readline()
        f.seek(0)
        if json_path.endswith('.jsonl') or (first_line.strip().startswith('{') and not first_line.strip().startswith('[')):
            # JSON Lines: one JSON object per line
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception as e:
                        print(f"Error parsing line: {line}\n{e}")
        else:
            # Standard JSON (array or object)
            records = json.load(f)
            if not isinstance(records, list):
                records = [records]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        timestamp DATETIME NOT NULL
    )''')
    inserted = 0
    for rec in records:
        try:
            c.execute('INSERT INTO visits (url, ip_address, user_agent, timestamp) VALUES (?, ?, ?, ?)',
                      (rec['url'], rec.get('ip', rec.get('ip_address', '')), rec.get('user_agent', ''), rec['timestamp']))
            inserted += 1
        except Exception as e:
            print(f"Error inserting record: {rec}\n{e}")
    conn.commit()
    conn.close()
    print(f"Imported {inserted} records from {json_path}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python import_historic.py path/to/historic.json")
        sys.exit(1)
    import_historic(sys.argv[1])
