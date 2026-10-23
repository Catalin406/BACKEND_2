# ============================================================
# PAGOS/APPS.PY / CONFIGURACIÓN DE LA APP PAGOS
# Pagos con Transbank Webpay Plus (ambiente de integración).
# ============================================================
from django.apps import AppConfig


class PagosConfig(AppConfig):
    """Configuración de la app pagos."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "pagos"
    verbose_name = "Pagos Webpay"
