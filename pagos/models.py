# ============================================================
# PAGOS/MODELS.PY / REGISTRO DE CADA INTENTO DE PAGO CON WEBPAY PLUS
# PagoWebpay guarda lo que Transbank respondió (token, orden de
# compra, códigos, últimos 4 dígitos) para auditar y para que el
# retorno sea idempotente. Una matrícula puede tener varios pagos
# (reintentos), pero solo uno puede terminar APROBADO.
# NUNCA se guarda el número completo de la tarjeta.
# ============================================================
from django.db import models


# ============================================================
# ESTADOS DEL PAGO
# ============================================================
class EstadoPago(models.TextChoices):
    """Ciclo de vida de un intento de pago."""

    INICIADO = "INICIADO", "Iniciado"
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    ANULADO_POR_USUARIO = "ANULADO_POR_USUARIO", "Anulado por el usuario"
    EXPIRADO = "EXPIRADO", "Expirado"
    REEMBOLSADO = "REEMBOLSADO", "Reembolsado"
    ERROR = "ERROR", "Error"


# ============================================================
# PAGO WEBPAY
# ============================================================
class PagoWebpay(models.Model):
    """Intento de pago de una matrícula en Webpay Plus."""

    matricula = models.ForeignKey(
        "matriculas.Matricula", verbose_name="matrícula", on_delete=models.PROTECT, related_name="pagos_webpay"
    )
    token = models.CharField("token de Webpay", max_length=64, unique=True)
    buy_order = models.CharField("orden de compra", max_length=26, unique=True)
    session_id = models.CharField("id de sesión", max_length=61)
    monto = models.PositiveIntegerField("monto (CLP)")
    estado = models.CharField(
        "estado", max_length=20, choices=EstadoPago.choices, default=EstadoPago.INICIADO, db_index=True
    )
    response_code = models.IntegerField("código de respuesta", null=True, blank=True)
    authorization_code = models.CharField("código de autorización", max_length=10, blank=True)
    payment_type_code = models.CharField("tipo de pago", max_length=5, blank=True)
    card_number = models.CharField("últimos 4 dígitos", max_length=4, blank=True)
    respuesta_cruda = models.JSONField("respuesta de Transbank", default=dict, blank=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "pago Webpay"
        verbose_name_plural = "pagos Webpay"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Pago {self.buy_order} · {self.get_estado_display()} · ${self.monto}"
