# ============================================================
# CURSOS/APPS.PY / CONFIGURACIÓN DE LA APP CURSOS
# Oferta académica: áreas de conocimiento y cursos/bootcamps.
# ============================================================
from django.apps import AppConfig


class CursosConfig(AppConfig):
    """Configuración de la app cursos."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "cursos"
    verbose_name = "Oferta académica"
