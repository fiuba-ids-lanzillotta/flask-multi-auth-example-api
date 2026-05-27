from flask import Blueprint, jsonify, request

from ..services.auth import (
    registrar_usuario,
    login_con_password,
    solicitar_password_reset,
    confirmar_password_reset,
    solicitar_login_code,
    verificar_login_code,
)

auth_bp = Blueprint('auth', __name__)


def _ejecutar(funcion, status_ok=200):
    """Wrapper que toma el body JSON, invoca la funcion del service y maneja errores."""
    body = request.get_json(silent=True)

    try:
        resultado = funcion(body)
    except ValueError as e:
        status = e.args[1] if len(e.args) > 1 else 400

        return jsonify(e.args[0]), status

    return jsonify(resultado), status_ok


@auth_bp.route('/register', methods=['POST'])
def post_register():
    return _ejecutar(registrar_usuario, status_ok=201)


@auth_bp.route('/login', methods=['POST'])
def post_login():
    return _ejecutar(login_con_password)


@auth_bp.route('/password-reset/request', methods=['POST'])
def post_password_reset_request():
    """Genera un token de reset y lo devuelve al web para que envie el email."""
    return _ejecutar(solicitar_password_reset)


@auth_bp.route('/password-reset/confirm', methods=['POST'])
def post_password_reset_confirm():
    return _ejecutar(confirmar_password_reset)


@auth_bp.route('/login-code/request', methods=['POST'])
def post_login_code_request():
    """Genera un codigo numerico y lo devuelve al web para que envie el email."""
    return _ejecutar(solicitar_login_code)


@auth_bp.route('/login-code/verify', methods=['POST'])
def post_login_code_verify():
    return _ejecutar(verificar_login_code)
