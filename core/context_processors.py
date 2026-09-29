# ============================================================
# CORE/CONTEXT_PROCESSORS.PY / DATOS GLOBALES PARA LAS PLANTILLAS
# Inyecta en todas las plantillas los datos de la alumna y el
# nombre comercial (leídos desde .env en settings), para que el
# footer nunca los tenga escritos a mano.
# ============================================================
from django.conf import settings


def datos_alumno(request):
    """Expone ALUMNO_NOMBRE, ALUMNO_SECCION, ALUMNO_ANIO y NOMBRE_COMERCIAL."""
    return {
        "ALUMNO_NOMBRE": settings.ALUMNO_NOMBRE,
        "ALUMNO_SECCION": settings.ALUMNO_SECCION,
        "ALUMNO_ANIO": settings.ALUMNO_ANIO,
        "NOMBRE_COMERCIAL": settings.NOMBRE_COMERCIAL,
    }
