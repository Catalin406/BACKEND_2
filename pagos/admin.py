# ============================================================
# PAGOS/ADMIN.PY / PAGOS WEBPAY EN DJANGO ADMIN (SOLO LECTURA)
# Un pago refleja dinero real (o de prueba) en Transbank: no se
# crea ni se edita a mano. Solo se consulta para auditoría.
# ============================================================
from django.contrib import admin

from .models import PagoWebpay


@admin.register(PagoWebpay)
class PagoWebpayAdmin(admin.ModelAdmin):
    """Admin de solo lectura."""

    list_display = ["buy_order", "matricula", "monto", "estado", "authorization_code", "card_number", "creado_en"]
    list_filter = ["estado", "creado_en"]
    search_fields = ["buy_order", "token", "matricula__codigo", "matricula__estudiante__username"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
