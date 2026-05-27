import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
import requests
from flask import request, jsonify

from .constants import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXP_HORAS,
    LOGIN_CODE_LEN,
    PASSWORD_RESET_TOKEN_BYTES,
    RECAPTCHA_DISABLED,
    RECAPTCHA_SECRET,
    RECAPTCHA_VERIFY_URL,
    ERROR_CODE_INVALID_MIN_VALUE,
    ERROR_CODE_INVALID_MAX_VALUE,
    ERROR_CODE_INVALID_EMAIL,
    ERROR_CODE_RECAPTCHA_FALTANTE,
    ERROR_CODE_RECAPTCHA_INVALIDO,
    ERROR_CODE_TOKEN_FALTANTE,
    ERROR_CODE_TOKEN_INVALIDO,
    ERROR_CODE_TOKEN_EXPIRADO,
)

logger = logging.getLogger(__name__)

# Expresion regular simple para validar emails
REGEX_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# ---------------------------------------------------------------
# Errores
# ---------------------------------------------------------------

def construir_error_api(code: str, message: str, description: str, level: str = 'error') -> dict:
    """Construye un payload de error compatible con el resto de la API."""
    return {
        'errors': [{
            'code': code,
            'message': message,
            'level': level,
            'description': description
        }]
    }


# ---------------------------------------------------------------
# Validaciones genericas
# ---------------------------------------------------------------

def validar_entero(numero, nombre: str = 'numero') -> int:
    try:
        return int(str(numero))
    except (ValueError, TypeError):
        raise ValueError(construir_error_api(
            code=f'invalid.{nombre}.format',
            message=f"Formato de '{nombre}' invalido",
            description=f"El valor '{numero}' no puede convertirse a un numero entero"
        ))


def validar_minimo(valor: int, minimo: int, nombre: str) -> int:
    if valor < minimo:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_INVALID_MIN_VALUE,
            message='Valor por debajo del minimo permitido',
            description=f"El parametro '{nombre}' debe ser mayor o igual a {minimo}. Se recibio: {valor}"
        ))

    return valor


def validar_string_no_vacio(valor, nombre: str) -> str:
    if valor is None or not str(valor).strip():
        raise ValueError(construir_error_api(
            code=f'required.{nombre}',
            message=f"Campo requerido: '{nombre}'",
            description=f"El campo '{nombre}' es obligatorio y no puede estar vacio"
        ))

    return str(valor).strip()


def validar_largo_string(valor: str, minimo: int, maximo: int, nombre: str) -> str:
    if len(valor) < minimo:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_INVALID_MIN_VALUE,
            message=f"Longitud minima no alcanzada en '{nombre}'",
            description=f"El campo '{nombre}' debe tener al menos {minimo} caracteres"
        ))

    if len(valor) > maximo:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_INVALID_MAX_VALUE,
            message=f"Longitud maxima superada en '{nombre}'",
            description=f"El campo '{nombre}' debe tener como maximo {maximo} caracteres"
        ))

    return valor


def validar_formato_email(email: str) -> str:
    if not REGEX_EMAIL.match(email):
        raise ValueError(construir_error_api(
            code=ERROR_CODE_INVALID_EMAIL,
            message="Formato de 'email' invalido",
            description=f"El valor '{email}' no es un email valido"
        ))

    return email.lower()


# ---------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------

def hashear_password(password: str) -> str:
    """Genera un hash bcrypt del password en texto plano."""
    hash_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    return hash_bytes.decode('utf-8')


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara un password en texto plano contra un hash bcrypt."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------
# Tokens y codigos de un solo uso
# ---------------------------------------------------------------

def generar_reset_token() -> str:
    """Genera un token random url-safe para el link de reseteo de password."""
    return secrets.token_urlsafe(PASSWORD_RESET_TOKEN_BYTES)


def generar_codigo_login() -> str:
    """Genera un codigo numerico de LOGIN_CODE_LEN digitos."""
    # secrets.randbelow garantiza distribucion uniforme criptograficamente segura.
    maximo = 10 ** LOGIN_CODE_LEN
    numero = secrets.randbelow(maximo)

    return str(numero).zfill(LOGIN_CODE_LEN)


def hashear_token(valor: str) -> str:
    """
    Hash SHA-256 del token/codigo para almacenarlo en la base.
    No usamos bcrypt porque estos tokens son random de alta entropia
    y se comparan por igualdad exacta de hash, no por verificacion lenta.
    """
    return hashlib.sha256(valor.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------
# JWT
# ---------------------------------------------------------------

def generar_jwt(usuario_id: int) -> str:
    """Genera un JWT firmado con el id del usuario."""
    ahora = datetime.now(timezone.utc)
    payload = {
        'sub': str(usuario_id),
        'iat': ahora,
        'exp': ahora + timedelta(hours=JWT_EXP_HORAS),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decodificar_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_TOKEN_EXPIRADO,
            message='Token expirado',
            description='El token de autenticacion expiro. Volve a iniciar sesion.'
        ), 401)
    except jwt.InvalidTokenError:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_TOKEN_INVALIDO,
            message='Token invalido',
            description='El token de autenticacion no es valido.'
        ), 401)


def extraer_jwt_del_header() -> str:
    header = request.headers.get('Authorization', '')

    if not header.startswith('Bearer '):
        raise ValueError(construir_error_api(
            code=ERROR_CODE_TOKEN_FALTANTE,
            message='Token de autenticacion faltante',
            description='Debe enviarse el header Authorization con el formato "Bearer <token>"'
        ), 401)

    return header[len('Bearer '):].strip()


def requiere_auth():
    """
    Decorador que valida el JWT del header Authorization e inyecta
    el payload en request.usuario_actual.
    """
    def decorador(funcion):
        @wraps(funcion)
        def wrapper(*args, **kwargs):
            try:
                token   = extraer_jwt_del_header()
                payload = decodificar_jwt(token)
            except ValueError as e:
                return jsonify(e.args[0]), e.args[1] if len(e.args) > 1 else 401

            request.usuario_actual = payload

            return funcion(*args, **kwargs)

        return wrapper

    return decorador


# ---------------------------------------------------------------
# reCAPTCHA v2
# ---------------------------------------------------------------

def validar_recaptcha(token: str) -> None:
    """
    Verifica el token contra Google. Si la verificacion falla, lanza
    ValueError con un error API listo para devolver al frontend.

    Si RECAPTCHA_DISABLED=true, se saltea la verificacion (solo para tests).
    """
    if RECAPTCHA_DISABLED:
        logger.warning('reCAPTCHA deshabilitado por configuracion (RECAPTCHA_DISABLED=true)')

        return

    if not token:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_RECAPTCHA_FALTANTE,
            message='reCAPTCHA faltante',
            description='Debe enviarse el campo "recaptcha_token" en el body con el valor del widget.'
        ), 400)

    if not RECAPTCHA_SECRET:
        logger.error('RECAPTCHA_SECRET no configurado en .env')

        raise ValueError(construir_error_api(
            code=ERROR_CODE_RECAPTCHA_INVALIDO,
            message='reCAPTCHA mal configurado en el servidor',
            description='Falta la variable RECAPTCHA_SECRET en el .env de la API.'
        ), 500)

    try:
        respuesta = requests.post(
            RECAPTCHA_VERIFY_URL,
            data={'secret': RECAPTCHA_SECRET, 'response': token},
            timeout=5,
        )
        cuerpo = respuesta.json()
    except requests.RequestException as e:
        logger.error(f'Error contactando reCAPTCHA: {e}')

        raise ValueError(construir_error_api(
            code=ERROR_CODE_RECAPTCHA_INVALIDO,
            message='Error verificando reCAPTCHA',
            description='No se pudo contactar el servicio de verificacion de Google.'
        ), 502)

    if not cuerpo.get('success'):
        codigos = cuerpo.get('error-codes', [])

        raise ValueError(construir_error_api(
            code=ERROR_CODE_RECAPTCHA_INVALIDO,
            message='reCAPTCHA invalido',
            description=f"Google rechazo el token. error-codes: {codigos}"
        ), 400)
