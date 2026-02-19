import sqlite3

def check_structure():
    conn = sqlite3.connect('soportes_v2.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(usuarios)")
    columns = cursor.fetchall()
    print("Columns Details:")
    for col in columns:
        cid, name, dtype, notnull, dflt_value, pk = col
        print(f"Index: {cid}, Name: '{name}', Type: {dtype}, PK: {pk}")
    
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM usuarios LIMIT 1").fetchone()
    if row:
        print("\nFirst Row Data:")
        for key in row.keys():
            print(f"Column '{key}': {row[key]} (Type: {type(row[key])})")
    else:
        print("\nNo rows found in 'usuarios'")

if __name__ == '__main__':
    check_structure()
