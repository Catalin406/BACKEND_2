# ============================================================
# CARRO/APPS.PY / CONFIGURACIÓN DE LA APP CARRO
# Carro de matrícula persistente (1 a 1) de cada estudiante.
# ============================================================
from django.apps import AppConfig


class CarroConfig(AppConfig):
    """Configuración de la app carro."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "carro"
    verbose_name = "Carro de matrícula"
