from uuid import UUID, uuid4
from datetime import datetime
from domain.models import Ticket, TicketStatus, TicketPriority, User
from infrastructure.persistence.repository import SQLiteRepository
from typing import List, Optional

class TicketService:
    def __init__(self, repository: SQLiteRepository):
        self.repository = repository

    def create_new_ticket(self, usuario_id: UUID, problema: str, categoria: str, prioridad_str: str) -> Ticket:
        """
        Business logic for creating a ticket.
        In a real app, this might involve:
        - Validating user exists.
        - Checking for duplicate tickets.
        - Sending a 'Ticket Created' email.
        """
        # Mapping string to Enum
        try:
            prioridad = TicketPriority(prioridad_str)
        except ValueError:
            prioridad = TicketPriority.MEDIA

        ticket = Ticket(
            id=uuid4(),
            usuario_id=usuario_id,
            problema=problema,
            categoria=categoria,
            prioridad=prioridad,
            estado=TicketStatus.ABIERTO,
            fecha_creacion=datetime.now()
        )
        
        return self.repository.create_ticket(ticket)

    def get_all_tickets_for_user(self, usuario_id: UUID) -> List[Ticket]:
        return self.repository.list_tickets(filters={'usuario_id': usuario_id})

    def resolve_ticket(self, ticket_id: UUID, tecnico_id: UUID, solucion: str) -> Optional[Ticket]:
        ticket = self.repository.get_ticket_by_id(ticket_id)
        if not ticket:
            return None
        
        ticket.estado = TicketStatus.RESUELTO
        ticket.tecnico_id = tecnico_id
        ticket.solucion = solucion
        ticket.fecha_finalizacion = datetime.now()
        
        # In a real app, we'd have a .update() method in repository
        # For now, let's assume we implement it in the repo next.
        return ticket
