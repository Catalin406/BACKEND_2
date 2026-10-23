# ============================================================
# PAGOS/VIEWS_HTML.PY / PAGO WEBPAY EN EL PANEL Y RETORNO DE WEBPAY
#  - panel_pagar_webpay (POST, solo coordinador): inicia el pago y
#    muestra una página que envía automáticamente token_ws a Webpay.
#  - webpay_retorno (GET y POST, sin login): a esta URL vuelve el
#    navegador desde Webpay; confirma el pago y muestra el resultado.
# ============================================================
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from core.excepciones import ErrorDeNegocio
from core.utilidades import obtener_o_redirigir
from matriculas.models import Matricula
from usuarios.permisos import solo_coordinador_para_escribir

from . import servicios
from .models import EstadoPago


# ============================================================
# INICIAR PAGO DESDE EL PANEL (COORDINADOR)
# ============================================================
@solo_coordinador_para_escribir
def panel_pagar_webpay(request, pk):
    """Crea la transacción Webpay y entrega el formulario que redirige a Webpay."""
    matricula, redireccion = obtener_o_redirigir(request, Matricula, pk=pk)
    if redireccion:
        return redireccion
    if request.method != "POST":
        return redirect("panel_matricula_detalle", pk=matricula.pk)
    try:
        return_url = request.build_absolute_uri(reverse("pagos_webpay_retorno"))
        pago, url = servicios.iniciar_pago_webpay(matricula, return_url)
    except ErrorDeNegocio as error:
        messages.error(request, error.mensaje)
        return redirect("panel_matricula_detalle", pk=matricula.pk)
    return render(request, "pagos/redireccion_webpay.html", {"url": url, "token": pago.token, "pago": pago})


# ============================================================
# RETORNO DESDE WEBPAY
# csrf_exempt es SEGURO aquí por dos motivos:
#  1) Es Transbank (a través del navegador del cliente) quien envía el
#     formulario desde OTRO dominio, así que no puede llevar nuestro
#     token CSRF. Sin la exención, Django lo rechazaría con 403.
#  2) Nada de lo que llega se cree: el token_ws solo se usa para
#     preguntar a Transbank, de servidor a servidor (commit), qué pasó.
#     Un atacante que invente parámetros solo obtiene "pago no encontrado".
#     Y el commit es idempotente, así que repetirlo no cobra dos veces.
# Acepta GET y POST porque Webpay usa ambos según el caso.
# ============================================================
@csrf_exempt
def webpay_retorno(request):
    """Interpreta el retorno de Webpay y muestra el resultado del pago."""
    parametros = request.GET if request.method == "GET" else request.POST
    usuario = request.user if request.user.is_authenticated else None
    try:
        pago = servicios.procesar_retorno(parametros, usuario)
    except ErrorDeNegocio as error:
        return render(request, "pagos/resultado.html", {"error": error.mensaje})
    if pago is None:
        return render(request, "pagos/resultado.html", {"error": "Faltan los datos de retorno de Webpay."})
    return render(request, "pagos/resultado.html", {
        "pago": pago, "matricula": pago.matricula, "estados": EstadoPago,
        "motivo": pago.respuesta_cruda.get("motivo", ""),
    })
