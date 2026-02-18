from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from typing import Optional

class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    TECNICO = "tecnico"

class TicketStatus(Enum):
    ABIERTO = "Abierto"
    EN_PROCESO = "En Proceso"
    RESUELTO = "Resuelto"
    CERRADO = "Cerrado"

class TicketPriority(Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    URGENTE = "Urgente"

@dataclass
class User:
    username: str
    email: str
    password_hash: str
    role: UserRole = UserRole.USER
    departamento: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    fecha_creacion: datetime = field(default_factory=datetime.now)

@dataclass
class Equipment:
    nombre_equipo: str
    tipo: Optional[str] = None
    marca_modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    fecha_compra: Optional[str] = None
    procesador: Optional[str] = None
    memoria_ram: Optional[str] = None
    tipo_ram: Optional[str] = None
    disco_duro: Optional[str] = None
    tipo_disco: Optional[str] = None
    color: Optional[str] = None
    notas: Optional[str] = None
    usuario_asignado_id: Optional[UUID] = None
    id: UUID = field(default_factory=uuid4)

@dataclass
class Ticket:
    usuario_id: UUID
    problema: str
    numero_ticket: Optional[int] = None
    categoria: str = "Otro"
    prioridad: TicketPriority = TicketPriority.MEDIA
    tecnico_id: Optional[UUID] = None
    equipo_id: Optional[UUID] = None
    estado: TicketStatus = TicketStatus.ABIERTO
    solucion: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    fecha_creacion: datetime = field(default_factory=datetime.now)
    fecha_finalizacion: Optional[datetime] = None

@dataclass
class TicketReadModel(Ticket):
    nombre_usuario: Optional[str] = None
    nombre_tecnico: Optional[str] = None
    nombre_equipo: Optional[str] = None
