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
# Al final del archivo está el equivalente para el PANEL HTML, que
# usa sesión de Django en vez de JWT: solo_coordinador_para_escribir.
# ============================================================
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
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


# ============================================================
# PANEL HTML: LECTURA ABIERTA, ESCRITURA SOLO DEL COORDINADOR
# La pauta deja la lectura pública, pero cualquier método que
# modifique (POST, PUT, PATCH, DELETE) exige una sesión de
# COORDINADOR. Sin esto, cualquiera en internet podría crear
# usuarios con rol COORDINADOR o desactivar cursos (IDOR/acceso
# roto). is_staff se sincroniza con el rol en Usuario.save().
# ============================================================
def es_coordinador_con_sesion(usuario):
    """True si hay sesión activa de un Coordinador Académico."""
    return bool(
        usuario.is_authenticated and usuario.is_active and usuario.is_staff and usuario.rol == Rol.COORDINADOR
    )


def solo_coordinador_para_escribir(vista):
    """Deja pasar GET/HEAD/OPTIONS; el resto exige sesión de coordinador."""

    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if request.method in SAFE_METHODS or es_coordinador_con_sesion(request.user):
            return vista(request, *args, **kwargs)
        if request.user.is_authenticated:
            messages.error(request, "Esta acción está reservada al Coordinador Académico. Inicia sesión con esa cuenta.")
        else:
            messages.warning(request, "Debes iniciar sesión como Coordinador Académico para modificar datos.")
        return redirect_to_login(request.get_full_path(), reverse("panel_login"))

    return envoltura
