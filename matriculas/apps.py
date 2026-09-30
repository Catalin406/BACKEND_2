# ============================================================
# MATRICULAS/APPS.PY / CONFIGURACIÓN DE LA APP MATRÍCULAS
# Matrículas, inscripciones oficiales UUID e historial de estados.
# ============================================================
from django.apps import AppConfig


class MatriculasConfig(AppConfig):
    """Configuración de la app matriculas."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "matriculas"
    verbose_name = "Matrículas"
