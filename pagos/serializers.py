# ============================================================
# PAGOS/SERIALIZERS.PY / RESPUESTAS DE LA API DE PAGOS WEBPAY
# Solo documentan (OpenAPI) lo que devuelven los endpoints de inicio
# de pago. El navegador debe enviar "token" a "url" con un formulario
# POST (campo token_ws) para abrir el formulario de Webpay.
# ============================================================
from rest_framework import serializers


class IniciarPagoRespuestaSerializer(serializers.Serializer):
    """Datos para redirigir al estudiante a Webpay."""

    mensaje = serializers.CharField()
    matricula_id = serializers.IntegerField()
    monto = serializers.IntegerField(help_text="Monto a cobrar en pesos chilenos.")
    buy_order = serializers.CharField(help_text="Orden de compra enviada a Transbank.")
    url = serializers.URLField(help_text="URL de Webpay a la que se envía el formulario.")
    token = serializers.CharField(help_text="Se envía a 'url' por POST en el campo token_ws.")
