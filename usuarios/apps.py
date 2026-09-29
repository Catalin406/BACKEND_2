# ============================================================
# USUARIOS/APPS.PY / CONFIGURACIÓN DE LA APP DE USUARIOS
# Registra las señales en ready() para que el carro de matrícula
# se cree automáticamente para cada estudiante.
# ============================================================
from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Configuración de la app usuarios."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
    verbose_name = "Usuarios"

    def ready(self):
        """Importa las señales al iniciar Django."""
        from . import signals  # noqa: F401
