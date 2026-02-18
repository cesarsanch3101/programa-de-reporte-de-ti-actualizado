import sqlite3
from uuid import UUID
from domain.models import TicketPriority, TicketStatus
from infrastructure.persistence.repository import SQLiteRepository

repo = SQLiteRepository('soportes_v2.db')

try:
    print("Listing tickets...")
    tickets = repo.list_tickets()
    print(f"Total tickets: {len(tickets)}")
    if tickets:
        print(f"First ticket: {tickets[0]}")
except Exception as e:
    print(f"Error listing tickets: {e}")

try:
    print("\nListing equipment...")
    equipos = repo.list_equipos()
    print(f"Total equipos: {len(equipos)}")
except Exception as e:
    print(f"Error listing equipos: {e}")
