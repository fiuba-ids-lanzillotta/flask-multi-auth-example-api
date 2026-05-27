from datetime import datetime

from sqlalchemy import create_engine, text

from .constants import DB_URL

# Motor de conexion compartido por toda la aplicacion.
# El pool de conexiones lo maneja SQLAlchemy automaticamente.
motor = create_engine(DB_URL, pool_pre_ping=True)


# ---------------------------------------------------------------
# Funciones de soporte
# ---------------------------------------------------------------

def fila_a_dict(fila) -> dict:
    """Convierte una fila del resultado de una query en un diccionario."""
    return dict(fila._mapping)


def ejecutar_consulta(sql: str, parametros: dict = None) -> list[dict]:
    """Ejecuta una SELECT y devuelve todas las filas como lista de dicts."""
    with motor.connect() as conexion:
        resultado = conexion.execute(text(sql), parametros or {})

        return [fila_a_dict(fila) for fila in resultado]


def ejecutar_mutacion(sql: str, parametros: dict = None) -> int:
    """
    Ejecuta un INSERT, UPDATE o DELETE y hace commit.
    Retorna el id autoincremental generado por el INSERT (0 si no aplica).
    """
    with motor.begin() as conexion:
        resultado = conexion.execute(text(sql), parametros or {})

        return resultado.lastrowid or 0


# ---------------------------------------------------------------
# Queries de usuarios
# ---------------------------------------------------------------

def obtener_usuario_por_id(usuario_id: int) -> dict:
    sql   = 'SELECT id, email, nombre FROM usuarios WHERE id = :id'
    filas = ejecutar_consulta(sql, {'id': usuario_id})

    return filas[0] if filas else {}


def obtener_usuario_por_email(email: str) -> dict:
    """Incluye el password_hash; usar solo en login y cambios de password."""
    sql   = 'SELECT id, email, nombre, password_hash FROM usuarios WHERE email = :email'
    filas = ejecutar_consulta(sql, {'email': email})

    return filas[0] if filas else {}


def insertar_usuario(email: str, nombre: str, password_hash: str) -> int:
    sql = """
        INSERT INTO usuarios (email, nombre, password_hash)
        VALUES (:email, :nombre, :password_hash)
    """

    return ejecutar_mutacion(sql, {
        'email':         email,
        'nombre':        nombre,
        'password_hash': password_hash,
    })


def actualizar_password(usuario_id: int, password_hash: str) -> None:
    sql = 'UPDATE usuarios SET password_hash = :password_hash WHERE id = :id'
    ejecutar_mutacion(sql, {'id': usuario_id, 'password_hash': password_hash})


# ---------------------------------------------------------------
# Queries de password_reset_tokens
# ---------------------------------------------------------------

def invalidar_password_reset_tokens(usuario_id: int) -> None:
    """Marca como usados todos los reset tokens vigentes del usuario."""
    sql = """
        UPDATE password_reset_tokens
           SET usado_en = NOW()
         WHERE usuario_id = :usuario_id
           AND usado_en IS NULL
    """
    ejecutar_mutacion(sql, {'usuario_id': usuario_id})


def insertar_password_reset_token(usuario_id: int, token_hash: str, expira_en: datetime) -> int:
    sql = """
        INSERT INTO password_reset_tokens (usuario_id, token_hash, expira_en)
        VALUES (:usuario_id, :token_hash, :expira_en)
    """

    return ejecutar_mutacion(sql, {
        'usuario_id': usuario_id,
        'token_hash': token_hash,
        'expira_en':  expira_en,
    })


def obtener_password_reset_token(token_hash: str) -> dict:
    sql   = """
        SELECT id, usuario_id, token_hash, expira_en, usado_en
          FROM password_reset_tokens
         WHERE token_hash = :token_hash
    """
    filas = ejecutar_consulta(sql, {'token_hash': token_hash})

    return filas[0] if filas else {}


def marcar_password_reset_token_usado(token_id: int) -> None:
    sql = 'UPDATE password_reset_tokens SET usado_en = NOW() WHERE id = :id'
    ejecutar_mutacion(sql, {'id': token_id})


# ---------------------------------------------------------------
# Queries de login_codes
# ---------------------------------------------------------------

def invalidar_login_codes(usuario_id: int) -> None:
    """Marca como usados todos los login codes vigentes del usuario."""
    sql = """
        UPDATE login_codes
           SET usado_en = NOW()
         WHERE usuario_id = :usuario_id
           AND usado_en IS NULL
    """
    ejecutar_mutacion(sql, {'usuario_id': usuario_id})


def insertar_login_code(usuario_id: int, codigo_hash: str, expira_en: datetime) -> int:
    sql = """
        INSERT INTO login_codes (usuario_id, codigo_hash, expira_en)
        VALUES (:usuario_id, :codigo_hash, :expira_en)
    """

    return ejecutar_mutacion(sql, {
        'usuario_id':  usuario_id,
        'codigo_hash': codigo_hash,
        'expira_en':   expira_en,
    })


def obtener_login_code_vigente(usuario_id: int, codigo_hash: str) -> dict:
    """Busca el ultimo login code del usuario con ese hash (cualquier estado)."""
    sql = """
        SELECT id, usuario_id, codigo_hash, expira_en, usado_en
          FROM login_codes
         WHERE usuario_id  = :usuario_id
           AND codigo_hash = :codigo_hash
         ORDER BY id DESC
         LIMIT 1
    """
    filas = ejecutar_consulta(sql, {
        'usuario_id':  usuario_id,
        'codigo_hash': codigo_hash,
    })

    return filas[0] if filas else {}


def marcar_login_code_usado(codigo_id: int) -> None:
    sql = 'UPDATE login_codes SET usado_en = NOW() WHERE id = :id'
    ejecutar_mutacion(sql, {'id': codigo_id})
