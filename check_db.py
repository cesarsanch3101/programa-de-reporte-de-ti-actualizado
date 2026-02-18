import sqlite3
conn = sqlite3.connect('soportes_v2.db')
cursor = conn.cursor()

print("Tables:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for t in tables:
    print(f"- {t[0]}")
    cursor.execute(f"SELECT COUNT(*) FROM {t[0]}")
    count = cursor.fetchone()[0]
    print(f"  Count: {count}")

print("\nConfiguración table check:")
try:
    cursor.execute("SELECT * FROM configuracion")
    print(f"Config rows: {len(cursor.fetchall())}")
except Exception as e:
    print(f"Error checking configuracion: {e}")

conn.close()
