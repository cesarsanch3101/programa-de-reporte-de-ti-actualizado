import sqlite3
from contextlib import contextmanager
from typing import List, Optional
from uuid import UUID
from domain.models import User, Ticket, Equipment, TicketStatus, TicketPriority, UserRole, TicketReadModel

class SQLiteRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    # --- Usuarios ---
    def get_user_by_username(self, username: str) -> Optional[User]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
            if row:
                return User(
                    id=UUID(row['id']),
                    username=row['username'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    role=UserRole(row['role']),
                    departamento=row['departamento'],
                    fecha_creacion=row['fecha_creacion']
                )
        return None

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (str(user_id),)).fetchone()
            if row:
                return User(
                    id=UUID(row['id']),
                    username=row['username'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    role=UserRole(row['role']),
                    departamento=row['departamento'],
                    fecha_creacion=row['fecha_creacion']
                )
        return None

    def list_users(self) -> List[User]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM usuarios ORDER BY username").fetchall()
            return [User(
                id=UUID(row['id']),
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                role=UserRole(row['role']),
                departamento=row['departamento'],
                fecha_creacion=row['fecha_creacion']
            ) for row in rows]

    def create_user(self, user: User) -> User:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO usuarios (id, username, email, password_hash, role, departamento)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(user.id), user.username, user.email, user.password_hash, 
                  user.role.value if isinstance(user.role, UserRole) else user.role, 
                  user.departamento))
            conn.commit()
        return user

    def update_user(self, user: User) -> User:
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE usuarios 
                SET email = ?, role = ?, password_hash = ?, departamento = ?
                WHERE id = ?
            """, (user.email, 
                  user.role.value if isinstance(user.role, UserRole) else user.role, 
                  user.password_hash, user.departamento, str(user.id)))
            conn.commit()
        return user

    def delete_user(self, user_id: UUID) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM usuarios WHERE id = ?", (str(user_id),))
            conn.commit()
            return cursor.rowcount > 0

    # --- Soportes (Tickets) ---
    def create_ticket(self, ticket: Ticket) -> Ticket:
        with self._get_connection() as conn:
            # Get next number if not provided
            if ticket.numero_ticket is None:
                row = conn.execute("SELECT MAX(numero_ticket) as max_num FROM soportes").fetchone()
                ticket.numero_ticket = (row['max_num'] or 0) + 1

            conn.execute("""
                INSERT INTO soportes (id, numero_ticket, usuario_id, tecnico_id, equipo_id, problema, estado, prioridad, categoria, solucion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(ticket.id), ticket.numero_ticket, str(ticket.usuario_id), 
                  str(ticket.tecnico_id) if ticket.tecnico_id else None,
                  str(ticket.equipo_id) if ticket.equipo_id else None,
                  ticket.problema, ticket.estado.value, ticket.prioridad.value, 
                  ticket.categoria, ticket.solucion))
            conn.commit()
        return ticket

    def get_ticket_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM soportes WHERE id = ?", (str(ticket_id),)).fetchone()
            if row:
                return Ticket(
                    id=UUID(row['id']),
                    numero_ticket=row['numero_ticket'],
                    usuario_id=UUID(row['usuario_id']),
                    problema=row['problema'],
                    categoria=row['categoria'],
                    prioridad=TicketPriority(row['prioridad']),
                    tecnico_id=UUID(row['tecnico_id']) if row['tecnico_id'] else None,
                    equipo_id=UUID(row['equipo_id']) if row['equipo_id'] else None,
                    estado=TicketStatus(row['estado']),
                    solucion=row['solucion'],
                    fecha_creacion=row['fecha_creacion'],
                    fecha_finalizacion=row['fecha_finalizacion']
                )
        return None

    def list_tickets(self, filters: dict = None) -> List[TicketReadModel]:
        query = """
            SELECT s.*, 
                   u.username as nombre_usuario, 
                   t.username as nombre_tecnico,
                   e.nombre_equipo
            FROM soportes s
            JOIN usuarios u ON s.usuario_id = u.id
            LEFT JOIN usuarios t ON s.tecnico_id = t.id
            LEFT JOIN equipos e ON s.equipo_id = e.id
            WHERE 1=1
        """
        params = []
        if filters:
            if 'estado' in filters:
                query += " AND s.estado = ?"
                params.append(filters['estado'])
            if 'usuario_id' in filters:
                query += " AND s.usuario_id = ?"
                params.append(str(filters['usuario_id']))

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [TicketReadModel(
                id=UUID(row['id']),
                numero_ticket=row['numero_ticket'],
                usuario_id=UUID(row['usuario_id']),
                problema=row['problema'],
                categoria=row['categoria'],
                prioridad=TicketPriority(row['prioridad']),
                tecnico_id=UUID(row['tecnico_id']) if row['tecnico_id'] else None,
                equipo_id=UUID(row['equipo_id']) if row['equipo_id'] else None,
                estado=TicketStatus(row['estado']),
                solucion=row['solucion'],
                fecha_creacion=row['fecha_creacion'],
                fecha_finalizacion=row['fecha_finalizacion'],
                nombre_usuario=row['nombre_usuario'],
                nombre_tecnico=row['nombre_tecnico'],
                nombre_equipo=row['nombre_equipo']
            ) for row in rows]

    def update_ticket(self, ticket: Ticket) -> Ticket:
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE soportes 
                SET estado = ?, tecnico_id = ?, solucion = ?, fecha_finalizacion = ?,
                    problema = ?, categoria = ?, prioridad = ?
                WHERE id = ?
            """, (ticket.estado.value, 
                  str(ticket.tecnico_id) if ticket.tecnico_id else None, 
                  ticket.solucion, 
                  ticket.fecha_finalizacion,
                  ticket.problema,
                  ticket.categoria,
                  ticket.prioridad.value,
                  str(ticket.id)))
            conn.commit()
        return ticket

    def delete_ticket(self, ticket_id: UUID) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM soportes WHERE id = ?", (str(ticket_id),))
            conn.commit()
            return cursor.rowcount > 0

    # --- Equipos ---
    def get_equipment_by_id(self, equipment_id: UUID) -> Optional[Equipment]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM equipos WHERE id = ?", (str(equipment_id),)).fetchone()
            if row:
                return Equipment(
                    id=UUID(row['id']),
                    nombre_equipo=row['nombre_equipo'],
                    tipo=row['tipo'],
                    marca_modelo=row['marca_modelo'],
                    numero_serie=row['numero_serie'],
                    fecha_compra=row['fecha_compra'],
                    procesador=row['procesador'],
                    memoria_ram=row['memoria_ram'],
                    tipo_ram=row['tipo_ram'],
                    disco_duro=row['disco_duro'],
                    tipo_disco=row['tipo_disco'],
                    color=row['color'],
                    notas=row['notas'],
                    usuario_asignado_id=UUID(row['usuario_asignado_id']) if row['usuario_asignado_id'] else None
                )
        return None

    def list_equipos(self) -> List[Equipment]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM equipos ORDER BY nombre_equipo").fetchall()
            return [Equipment(
                id=UUID(row['id']),
                nombre_equipo=row['nombre_equipo'],
                tipo=row['tipo'],
                marca_modelo=row['marca_modelo'],
                numero_serie=row['numero_serie'],
                fecha_compra=row['fecha_compra'],
                procesador=row['procesador'],
                memoria_ram=row['memoria_ram'],
                tipo_ram=row['tipo_ram'],
                disco_duro=row['disco_duro'],
                tipo_disco=row['tipo_disco'],
                color=row['color'],
                notas=row['notas'],
                usuario_asignado_id=UUID(row['usuario_asignado_id']) if row['usuario_asignado_id'] else None
            ) for row in rows]

    def create_equipment(self, equipment: Equipment) -> Equipment:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO equipos (
                    id, nombre_equipo, tipo, marca_modelo, numero_serie, fecha_compra,
                    procesador, memoria_ram, tipo_ram, disco_duro, tipo_disco, color, notas, usuario_asignado_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(equipment.id), equipment.nombre_equipo, equipment.tipo, equipment.marca_modelo, 
                  equipment.numero_serie, equipment.fecha_compra, equipment.procesador, equipment.memoria_ram,
                  equipment.tipo_ram, equipment.disco_duro, equipment.tipo_disco, equipment.color, equipment.notas,
                  str(equipment.usuario_asignado_id) if equipment.usuario_asignado_id else None))
            conn.commit()
        return equipment

    def update_equipment(self, equipment: Equipment) -> Equipment:
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE equipos SET 
                    nombre_equipo=?, tipo=?, marca_modelo=?, numero_serie=?, fecha_compra=?,
                    procesador=?, memoria_ram=?, tipo_ram=?, disco_duro=?, tipo_disco=?, color=?, notas=?,
                    usuario_asignado_id=? 
                WHERE id=?
            """, (equipment.nombre_equipo, equipment.tipo, equipment.marca_modelo, equipment.numero_serie,
                  equipment.fecha_compra, equipment.procesador, equipment.memoria_ram, equipment.tipo_ram,
                  equipment.disco_duro, equipment.tipo_disco, equipment.color, equipment.notas,
                  str(equipment.usuario_asignado_id) if equipment.usuario_asignado_id else None,
                  str(equipment.id)))
            conn.commit()
        return equipment
