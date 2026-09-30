# ============================================================
# USUARIOS/PERMISOS.PY / PERMISOS REUTILIZABLES POR ROL
# Implementan la matriz de roles de la pauta:
#   PÚBLICO     -> lectura de cursos y áreas
#   ESTUDIANTE  -> carro, confirmar matrícula, mis matrículas
#   COORDINADOR -> escritura de cursos/áreas/usuarios y estados
# El rol se lee del claim "rol" del JWT (request.auth) y se
# contrasta con el rol real del usuario en la BD y con is_active,
# para que un token antiguo no conserve privilegios revocados.
# Sin token -> 401 (DRF usa el header WWW-Authenticate de JWT);
# con token y rol incorrecto -> 403.
# ============================================================
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Rol


def rol_del_token(request):
    """Devuelve el claim 'rol' del JWT de la petición, o None."""
    token = getattr(request, "auth", None)
    if token is None:
        return None
    try:
        return token.get("rol")
    except AttributeError:
        return None


# ============================================================
# BASE: PERMISO POR ROL
# ============================================================
class _PermisoPorRol(BasePermission):
    """Autenticado, activo y con el mismo rol en el token y en la BD."""

    rol_requerido = None
    message = "No tienes permisos para realizar esta acción con tu rol."

    def has_permission(self, request, view):
        usuario = request.user
        if not (usuario and usuario.is_authenticated and usuario.is_active):
            return False
        return rol_del_token(request) == self.rol_requerido and usuario.rol == self.rol_requerido


class EsCoordinador(_PermisoPorRol):
    """Solo el Coordinador Académico."""

    rol_requerido = Rol.COORDINADOR
    message = "Esta acción está reservada al Coordinador Académico."


class EsEstudiante(_PermisoPorRol):
    """Solo estudiantes."""

    rol_requerido = Rol.ESTUDIANTE
    message = "Esta acción está reservada a estudiantes."


# ============================================================
# LECTURA PÚBLICA / ESCRITURA DEL COORDINADOR
# ============================================================
class EsCoordinadorOSoloLectura(BasePermission):
    """GET, HEAD y OPTIONS para cualquiera; escritura solo coordinador."""

    message = EsCoordinador.message

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return EsCoordinador().has_permission(request, view)


# ============================================================
# PERMISO A NIVEL DE OBJETO
# ============================================================
class EsPropietarioDeLaMatricula(BasePermission):
    """El estudiante solo accede a sus propias matrículas."""

    message = "Esta matrícula no te pertenece."

    def has_object_permission(self, request, view, obj):
        return obj.estudiante_id == request.user.id
