"""Servicios de autenticacion.

Cuatro flujos soportados:
1. Registro de usuario.
2. Login clasico con email + password.
3. Reseteo de password via link enviado por email (request + confirm).
4. Login passwordless via codigo numerico enviado por email (request + verify).

En todos los flujos sensibles se valida el reCAPTCHA antes de cualquier
operacion en la base.
"""
from datetime import datetime, timedelta, timezone

from ..constants import (
    PASSWORD_RESET_TOKEN_EXP_MIN,
    LOGIN_CODE_EXP_MIN,
    ERROR_CODE_CREDENCIALES,
    ERROR_CODE_EMAIL_YA_REGISTRADO,
    ERROR_CODE_RESET_TOKEN_INVALIDO,
    ERROR_CODE_RESET_TOKEN_EXPIRADO,
    ERROR_CODE_RESET_TOKEN_USADO,
    ERROR_CODE_LOGIN_CODE_INVALIDO,
    ERROR_CODE_LOGIN_CODE_EXPIRADO,
    ERROR_CODE_LOGIN_CODE_USADO,
    ERROR_CODE_USUARIO_NOT_FOUND,
)
from ..utils import (
    construir_error_api,
    hashear_password,
    verificar_password,
    generar_jwt,
    generar_reset_token,
    generar_codigo_login,
    hashear_token,
    validar_recaptcha,
)
from ..validators.auth import (
    validar_body_login,
    validar_body_registro,
    validar_body_solo_email,
    validar_body_password_reset_confirm,
    validar_body_login_code_verify,
)
from .. import db
from .usuarios import construir_usuario_dto


# ---------------------------------------------------------------
# 1. Registro
# ---------------------------------------------------------------

def registrar_usuario(body: dict) -> dict:
    datos = validar_body_registro(body)
    validar_recaptcha(datos['recaptcha_token'])

    if db.obtener_usuario_por_email(datos['email']):
        raise ValueError(construir_error_api(
            code=ERROR_CODE_EMAIL_YA_REGISTRADO,
            message='Email ya registrado',
            description=f"Ya existe un usuario con email '{datos['email']}'"
        ), 409)

    nuevo_id = db.insertar_usuario(
        email=datos['email'],
        nombre=datos['nombre'],
        password_hash=hashear_password(datos['password']),
    )

    return construir_usuario_dto({
        'id':     nuevo_id,
        'email':  datos['email'],
        'nombre': datos['nombre'],
    })


# ---------------------------------------------------------------
# 2. Login clasico (email + password)
# ---------------------------------------------------------------

def login_con_password(body: dict) -> dict:
    datos = validar_body_login(body)
    validar_recaptcha(datos['recaptcha_token'])

    usuario = db.obtener_usuario_por_email(datos['email'])

    if not usuario or not verificar_password(datos['password'], usuario['password_hash']):
        raise ValueError(construir_error_api(
            code=ERROR_CODE_CREDENCIALES,
            message='Credenciales invalidas',
            description='El email o password son incorrectos'
        ), 401)

    return {
        'token':   generar_jwt(usuario_id=usuario['id']),
        'usuario': construir_usuario_dto(usuario),
    }


# ---------------------------------------------------------------
# 3. Reseteo de password
# ---------------------------------------------------------------

def solicitar_password_reset(body: dict) -> dict:
    """
    Valida captcha, genera un token y lo guarda hasheado.
    Retorna {token, usuario} para que el web arme el link y mande el email.

    Nota didactica: en un sistema real la API nunca deberia retornar el token
    al cliente; en su lugar se enviaria el email desde el mismo proceso. Aca
    el web es responsable del envio (porque tiene los templates Jinja), asi
    que aceptamos exponer el token al web confiado y lo documentamos.
    """
    datos = validar_body_solo_email(body)
    validar_recaptcha(datos['recaptcha_token'])

    usuario = db.obtener_usuario_por_email(datos['email'])

    if not usuario:
        # Devolvemos 404 explicito; el web puede traducirlo a un mensaje
        # neutro al usuario final ("si el email existe, te llegara un mail")
        # para no filtrar la existencia de cuentas.
        raise ValueError(construir_error_api(
            code=ERROR_CODE_USUARIO_NOT_FOUND,
            message='Usuario no encontrado',
            description=f"No existe un usuario con email '{datos['email']}'"
        ), 404)

    # Invalidamos tokens previos para que no convivan multiples links activos.
    db.invalidar_password_reset_tokens(usuario['id'])

    token     = generar_reset_token()
    expira_en = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXP_MIN)

    db.insertar_password_reset_token(
        usuario_id=usuario['id'],
        token_hash=hashear_token(token),
        expira_en=expira_en,
    )

    return {
        'token':              token,
        'expira_en':          expira_en.isoformat(),
        'usuario':            construir_usuario_dto(usuario),
    }


def confirmar_password_reset(body: dict) -> dict:
    """Cambia el password usando un token de reseteo vigente."""
    datos = validar_body_password_reset_confirm(body)

    registro = db.obtener_password_reset_token(hashear_token(datos['token']))

    if not registro:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_RESET_TOKEN_INVALIDO,
            message='Token de reseteo invalido',
            description='El token no existe o ya fue invalidado.'
        ), 400)

    if registro['usado_en'] is not None:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_RESET_TOKEN_USADO,
            message='Token ya utilizado',
            description='El token ya fue usado para resetear el password. Solicita uno nuevo.'
        ), 400)

    if registro['expira_en'] < datetime.now():
        raise ValueError(construir_error_api(
            code=ERROR_CODE_RESET_TOKEN_EXPIRADO,
            message='Token expirado',
            description='El token de reseteo expiro. Solicita uno nuevo.'
        ), 400)

    db.actualizar_password(
        usuario_id=registro['usuario_id'],
        password_hash=hashear_password(datos['password']),
    )
    db.marcar_password_reset_token_usado(registro['id'])

    usuario = db.obtener_usuario_por_id(registro['usuario_id'])

    return {'usuario': construir_usuario_dto(usuario)}


# ---------------------------------------------------------------
# 4. Login passwordless con codigo de un solo uso
# ---------------------------------------------------------------

def solicitar_login_code(body: dict) -> dict:
    """Genera y guarda un codigo de un solo uso, lo devuelve para que el web lo emaile."""
    datos = validar_body_solo_email(body)
    validar_recaptcha(datos['recaptcha_token'])

    usuario = db.obtener_usuario_por_email(datos['email'])

    if not usuario:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_USUARIO_NOT_FOUND,
            message='Usuario no encontrado',
            description=f"No existe un usuario con email '{datos['email']}'"
        ), 404)

    db.invalidar_login_codes(usuario['id'])

    codigo    = generar_codigo_login()
    expira_en = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_CODE_EXP_MIN)

    db.insertar_login_code(
        usuario_id=usuario['id'],
        codigo_hash=hashear_token(codigo),
        expira_en=expira_en,
    )

    return {
        'codigo':    codigo,
        'expira_en': expira_en.isoformat(),
        'usuario':   construir_usuario_dto(usuario),
    }


def verificar_login_code(body: dict) -> dict:
    datos = validar_body_login_code_verify(body)

    usuario = db.obtener_usuario_por_email(datos['email'])

    if not usuario:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_LOGIN_CODE_INVALIDO,
            message='Codigo invalido',
            description='El codigo no es valido para este email.'
        ), 400)

    registro = db.obtener_login_code_vigente(
        usuario_id=usuario['id'],
        codigo_hash=hashear_token(datos['codigo']),
    )

    if not registro:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_LOGIN_CODE_INVALIDO,
            message='Codigo invalido',
            description='El codigo no es valido para este email.'
        ), 400)

    if registro['usado_en'] is not None:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_LOGIN_CODE_USADO,
            message='Codigo ya utilizado',
            description='Este codigo ya fue usado. Solicita uno nuevo.'
        ), 400)

    if registro['expira_en'] < datetime.now():
        raise ValueError(construir_error_api(
            code=ERROR_CODE_LOGIN_CODE_EXPIRADO,
            message='Codigo expirado',
            description='El codigo expiro. Solicita uno nuevo.'
        ), 400)

    db.marcar_login_code_usado(registro['id'])

    return {
        'token':   generar_jwt(usuario_id=usuario['id']),
        'usuario': construir_usuario_dto(usuario),
    }
