from ..constants import (
    PASSWORD_MIN_LEN,
    PASSWORD_MAX_LEN,
    LOGIN_CODE_LEN,
    ERROR_CODE_INVALID_BODY,
)
from ..utils import (
    construir_error_api,
    validar_string_no_vacio,
    validar_largo_string,
    validar_formato_email,
)


def _validar_body_presente(body):
    if body is None:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_INVALID_BODY,
            message='Cuerpo de la solicitud invalido',
            description='El cuerpo debe ser un JSON valido con Content-Type application/json'
        ))


def _recoger(body, nombre, fn):
    """Ejecuta fn() y devuelve (valor, errores) acumulando los errores en formato API."""
    try:
        return fn(), []
    except ValueError as e:
        return None, list(e.args[0]['errors'])


def _extraer_recaptcha(body):
    """
    El token del widget es siempre opcional a nivel formato (puede venir vacio);
    si esta deshabilitado o invalido se valida luego en utils.validar_recaptcha.
    """
    return body.get('recaptcha_token') or ''


def validar_body_registro(body: dict) -> dict:
    """POST /register: email, nombre, password, recaptcha_token."""
    _validar_body_presente(body)

    errores = []

    email, e1 = _recoger(body, 'email', lambda: validar_formato_email(
        validar_string_no_vacio(body.get('email'), 'email')
    ))
    errores.extend(e1)

    nombre, e2 = _recoger(body, 'nombre', lambda: validar_largo_string(
        validar_string_no_vacio(body.get('nombre'), 'nombre'), 1, 100, 'nombre'
    ))
    errores.extend(e2)

    password, e3 = _recoger(body, 'password', lambda: validar_largo_string(
        validar_string_no_vacio(body.get('password'), 'password'),
        PASSWORD_MIN_LEN, PASSWORD_MAX_LEN, 'password'
    ))
    errores.extend(e3)

    if errores:
        raise ValueError({'errors': errores})

    return {
        'email':           email,
        'nombre':          nombre,
        'password':        password,
        'recaptcha_token': _extraer_recaptcha(body),
    }


def validar_body_login(body: dict) -> dict:
    """POST /login: email, password, recaptcha_token."""
    _validar_body_presente(body)

    errores = []

    email, e1 = _recoger(body, 'email', lambda: validar_formato_email(
        validar_string_no_vacio(body.get('email'), 'email')
    ))
    errores.extend(e1)

    password, e2 = _recoger(body, 'password', lambda: validar_string_no_vacio(
        body.get('password'), 'password'
    ))
    errores.extend(e2)

    if errores:
        raise ValueError({'errors': errores})

    return {
        'email':           email,
        'password':        password,
        'recaptcha_token': _extraer_recaptcha(body),
    }


def validar_body_solo_email(body: dict) -> dict:
    """Body con email + captcha: usado por /password-reset/request y /login-code/request."""
    _validar_body_presente(body)

    errores = []

    email, e1 = _recoger(body, 'email', lambda: validar_formato_email(
        validar_string_no_vacio(body.get('email'), 'email')
    ))
    errores.extend(e1)

    if errores:
        raise ValueError({'errors': errores})

    return {
        'email':           email,
        'recaptcha_token': _extraer_recaptcha(body),
    }


def validar_body_password_reset_confirm(body: dict) -> dict:
    """POST /password-reset/confirm: token + nuevo password."""
    _validar_body_presente(body)

    errores = []

    token, e1 = _recoger(body, 'token', lambda: validar_string_no_vacio(body.get('token'), 'token'))
    errores.extend(e1)

    password, e2 = _recoger(body, 'password', lambda: validar_largo_string(
        validar_string_no_vacio(body.get('password'), 'password'),
        PASSWORD_MIN_LEN, PASSWORD_MAX_LEN, 'password'
    ))
    errores.extend(e2)

    if errores:
        raise ValueError({'errors': errores})

    return {'token': token, 'password': password}


def validar_body_login_code_verify(body: dict) -> dict:
    """POST /login-code/verify: email + codigo."""
    _validar_body_presente(body)

    errores = []

    email, e1 = _recoger(body, 'email', lambda: validar_formato_email(
        validar_string_no_vacio(body.get('email'), 'email')
    ))
    errores.extend(e1)

    codigo, e2 = _recoger(body, 'codigo', lambda: validar_largo_string(
        validar_string_no_vacio(body.get('codigo'), 'codigo'),
        LOGIN_CODE_LEN, LOGIN_CODE_LEN, 'codigo'
    ))
    errores.extend(e2)

    if errores:
        raise ValueError({'errors': errores})

    return {'email': email, 'codigo': codigo}
