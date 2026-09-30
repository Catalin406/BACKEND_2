# ============================================================
# CORE/APPS.PY / CONFIGURACIÓN DE LA APP CORE
# Núcleo del sitio: inicio, documentación, redirección de rutas,
# utilidades compartidas y comandos de gestión.
# ============================================================
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuración de la app core."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Núcleo"
