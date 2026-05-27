from ..constants import ERROR_CODE_USUARIO_NOT_FOUND
from ..utils import construir_error_api
from .. import db


def construir_usuario_dto(usuario: dict) -> dict:
    """DTO publico de un usuario (sin password_hash)."""
    return {
        'id':     usuario['id'],
        'email':  usuario['email'],
        'nombre': usuario['nombre'],
    }


def buscar_usuario_por_id(usuario_id: int) -> dict:
    usuario = db.obtener_usuario_por_id(usuario_id)

    if not usuario:
        return {}

    return construir_usuario_dto(usuario)


def buscar_usuario_por_id_o_error(usuario_id: int) -> dict:
    usuario = buscar_usuario_por_id(usuario_id)

    if not usuario:
        raise ValueError(construir_error_api(
            code=ERROR_CODE_USUARIO_NOT_FOUND,
            message='Usuario no encontrado',
            description=f"No existe un usuario con id '{usuario_id}'"
        ), 404)

    return usuario
