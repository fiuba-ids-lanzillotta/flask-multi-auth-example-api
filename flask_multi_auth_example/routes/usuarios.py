from flask import Blueprint, jsonify, request

from ..constants import ERROR_CODE_USUARIO_NOT_FOUND
from ..utils import construir_error_api, requiere_auth
from ..services.usuarios import buscar_usuario_por_id

usuarios_bp = Blueprint('usuarios', __name__)


@usuarios_bp.route('/me', methods=['GET'])
@requiere_auth()
def get_me():
    """Retorna el usuario autenticado a partir del JWT."""
    payload    = request.usuario_actual
    usuario_id = int(payload['sub'])
    usuario    = buscar_usuario_por_id(usuario_id)

    if not usuario:
        return jsonify(construir_error_api(
            code=ERROR_CODE_USUARIO_NOT_FOUND,
            message='Usuario no encontrado',
            description=f"No existe un usuario con id '{usuario_id}'"
        )), 404

    return jsonify(usuario)
