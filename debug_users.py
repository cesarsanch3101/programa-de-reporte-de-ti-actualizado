import sqlite3
from config import Config

def check_users():
    conn = sqlite3.connect('soportes_v2.db')
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT * FROM usuarios").fetchall()
    print(f"Total users: {len(users)}")
    if users:
        print("First user keys:", users[0].keys())
        for user in users:
            print(f"ID: {user['id']}, Username: {user['username']}")

if __name__ == '__main__':
    check_users()
