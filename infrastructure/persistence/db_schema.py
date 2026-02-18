SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    departamento TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equipos (
    id TEXT PRIMARY KEY,
    nombre_equipo TEXT UNIQUE NOT NULL,
    tipo TEXT,
    marca_modelo TEXT,
    numero_serie TEXT UNIQUE,
    fecha_compra DATE,
    procesador TEXT,
    memoria_ram TEXT,
    tipo_ram TEXT,
    disco_duro TEXT,
    tipo_disco TEXT,
    color TEXT,
    notas TEXT,
    usuario_asignado_id TEXT,
    FOREIGN KEY (usuario_asignado_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS soportes (
    id TEXT PRIMARY KEY,
    numero_ticket INTEGER UNIQUE,
    usuario_id TEXT NOT NULL,
    tecnico_id TEXT,
    equipo_id TEXT,
    problema TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Abierto',
    prioridad TEXT NOT NULL DEFAULT 'Media',
    categoria TEXT NOT NULL DEFAULT 'Otro',
    solucion TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_finalizacion TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    FOREIGN KEY (tecnico_id) REFERENCES usuarios (id) ON DELETE SET NULL,
    FOREIGN KEY (equipo_id) REFERENCES equipos (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS mantenimientos (
    id TEXT PRIMARY KEY,
    equipo_id TEXT NOT NULL,
    titulo TEXT NOT NULL,
    fecha_programada DATE NOT NULL,
    estado TEXT DEFAULT 'Pendiente',
    tecnico_asignado_id TEXT,
    motivo_reprogramacion TEXT,
    FOREIGN KEY (equipo_id) REFERENCES equipos (id) ON DELETE CASCADE,
    FOREIGN KEY (tecnico_asignado_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS auditoria_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT,
    accion TEXT NOT NULL,
    detalles TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS legacy_migration_map (
    old_id INTEGER,
    new_uuid TEXT PRIMARY KEY,
    table_name TEXT,
    UNIQUE(old_id, table_name)
);

CREATE INDEX IF NOT EXISTS idx_soportes_usuario ON soportes (usuario_id, fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_soportes_estado ON soportes (estado, prioridad);

CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT
);
"""
