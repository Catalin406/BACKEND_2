# ============================================================
# CORE/FABRICAS.PY / DATOS MÍNIMOS PARA LAS PRUEBAS AUTOMATIZADAS
# Funciones que crean usuarios, áreas y cursos válidos, y un helper
# para iniciar sesión por JWT en APITestCase. Evitan repetir datos
# en cada archivo tests.py.
# ============================================================
from datetime import date
from itertools import count

from cursos.models import AreaConocimiento, Curso, Modalidad, TipoCurso
from usuarios.models import Rol, Usuario

CLAVE = "ClaveSegura2026!"
_secuencia = count(1)


def crear_usuario(username, rol=Rol.ESTUDIANTE, **extra):
    """Crea un usuario con contraseña CLAVE."""
    usuario = Usuario(username=username, email=f"{username}@prueba.cl", rol=rol, **extra)
    usuario.set_password(CLAVE)
    usuario.save()
    return usuario


def crear_area(nombre=None, **extra):
    """Crea un área activa."""
    return AreaConocimiento.objects.create(nombre=nombre or f"Área {next(_secuencia)}", **extra)


def crear_curso(area=None, titulo=None, cupos=10, costo=100000, **extra):
    """Crea un curso activo con 'cupos' cupos."""
    datos = {
        "titulo": titulo or f"Curso {next(_secuencia)}",
        "descripcion": "Descripción de prueba.",
        "area": area or crear_area(),
        "tipo": TipoCurso.CURSO,
        "modalidad": Modalidad.ONLINE,
        "costo_matricula": costo,
        "fecha_inicio": date(2027, 1, 10),
        "fecha_termino": date(2027, 2, 10),
        "cupos_maximos": cupos,
    }
    datos.update(extra)
    return Curso.objects.create(**datos)


def autenticar(cliente, usuario):
    """Hace login JWT real y deja el header Authorization en el cliente."""
    respuesta = cliente.post("/api/auth/login/", {"username": usuario.username, "password": CLAVE}, format="json")
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return respuesta.data
