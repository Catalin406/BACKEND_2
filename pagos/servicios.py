# ============================================================
# PAGOS/SERVICIOS.PY / INTEGRACIÓN CON TRANSBANK WEBPAY PLUS
# Flujo: iniciar_pago_webpay -> (el estudiante paga en Webpay) ->
# procesar_retorno -> confirmar_pago_webpay (commit) ->
# matriculas.servicios.pagar_matricula.
# REGLA DE ORO: nunca puede quedar un cobro aprobado en Transbank sin
# que su matrícula haya pasado a PAGADO por ESE mismo pago. Si el
# cobro se aprobó pero la matrícula ya no se puede pagar (sin cupos,
# curso inactivo, ya inscrito, ya pagada por otro pago, etc.), se
# hace refund automático y el pago queda REEMBOLSADO.
# Los nombres del SDK (transbank-sdk 6.1.0) se verificaron leyendo su código:
# Transaction.build_for_integration / build_for_production, create,
# commit, refund y TransbankError.
# ============================================================
import logging
import uuid

import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import Transaction

from core.excepciones import ErrorDeNegocio
from matriculas.models import EstadoMatricula, Matricula
from matriculas.servicios import pagar_matricula

from .models import EstadoPago, PagoWebpay

registro = logging.getLogger(__name__)

# Tiempo máximo de espera a Transbank (el SDK trae 600 s por defecto: demasiado
# para mantener un bloqueo de base de datos mientras se espera).
TIMEOUT_TRANSBANK = 30


# ============================================================
# EXCEPCIONES PROPIAS
# ============================================================
class MatriculaNoPagableError(ErrorDeNegocio):
    """La matrícula no está PENDIENTE o no tiene monto a cobrar (409)."""

    codigo_http = status.HTTP_409_CONFLICT
    mensaje_por_defecto = "Esta matrícula no se puede pagar: debe estar PENDIENTE y tener un total mayor a $0."


class WebpayNoDisponibleError(ErrorDeNegocio):
    """Transbank no respondió o rechazó la creación de la transacción (502)."""

    codigo_http = status.HTTP_502_BAD_GATEWAY
    mensaje_por_defecto = "No fue posible comunicarse con Webpay. Intenta nuevamente en unos minutos."


class PagoNoEncontradoError(ErrorDeNegocio):
    """El token o la orden de compra no corresponden a un pago registrado (404)."""

    codigo_http = status.HTTP_404_NOT_FOUND
    mensaje_por_defecto = "No encontramos el pago asociado a esta operación."


# ============================================================
# CLIENTE DE TRANSBANK
# Integración usa Transaction.build_for_integration con las
# credenciales de settings (por defecto las constantes públicas del
# SDK). Las pruebas reemplazan esta función por un mock.
# ============================================================
def _transaccion():
    """Devuelve el Transaction de Webpay Plus según TRANSBANK_AMBIENTE."""
    if settings.TRANSBANK_AMBIENTE == "produccion":
        tx = Transaction.build_for_production(settings.TRANSBANK_CODIGO_COMERCIO, settings.TRANSBANK_API_KEY)
    else:
        tx = Transaction.build_for_integration(settings.TRANSBANK_CODIGO_COMERCIO, settings.TRANSBANK_API_KEY)
    tx.options.timeout = TIMEOUT_TRANSBANK
    return tx


# ============================================================
# INICIAR PAGO
# Crea la transacción en Transbank y guarda el PagoWebpay INICIADO.
# El monto se calcula en el servidor desde los costos congelados:
# el cliente jamás envía cuánto pagar.
# ============================================================
def iniciar_pago_webpay(matricula, return_url):
    """Devuelve (pago, url_webpay). El navegador debe enviar token_ws a esa url por POST."""
    matricula = Matricula.objects.select_related("estudiante").get(pk=matricula.pk)
    monto = int(matricula.total)
    if matricula.estado != EstadoMatricula.PENDIENTE or monto <= 0:
        raise MatriculaNoPagableError()

    buy_order = f"M{matricula.pk}-{uuid.uuid4().hex[:12]}"[:26]
    session_id = f"est-{matricula.estudiante_id}"
    try:
        respuesta = _transaccion().create(buy_order, session_id, monto, return_url)
        token, url = respuesta["token"], respuesta["url"]
    except (TransbankError, requests.RequestException, KeyError) as error:
        registro.error("No se pudo crear la transacción Webpay de la matrícula %s: %r", matricula.pk, error)
        raise WebpayNoDisponibleError() from error

    pago = PagoWebpay.objects.create(
        matricula=matricula, token=token, buy_order=buy_order, session_id=session_id, monto=monto,
        respuesta_cruda={"create": respuesta},
    )
    return pago, url


# ============================================================
# CONFIRMAR PAGO (COMMIT) · IDEMPOTENTE
# 1) Bloquea la fila del pago: si el retorno llega dos veces a la
#    vez, el segundo espera y luego ve un estado final -> no repite.
# 2) Si ya no está INICIADO, devuelve el resultado guardado sin
#    llamar a Transbank ni tocar cupos.
# 3) commit servidor a servidor: Transbank dice si se autorizó.
# 4) Si AUTHORIZED y response_code == 0 -> pagar_matricula. Ante
#    CUALQUIER fallo de esa etapa se hace refund automático.
# ============================================================
def confirmar_pago_webpay(token, usuario=None):
    """Confirma con Transbank el pago de 'token' y devuelve el PagoWebpay actualizado."""
    with transaction.atomic():
        pago = PagoWebpay.objects.select_for_update().select_related("matricula").filter(token=token).first()
        if pago is None:
            raise PagoNoEncontradoError()
        if pago.estado != EstadoPago.INICIADO:
            return pago  # Idempotencia: ya fue procesado.

        tx = _transaccion()
        try:
            respuesta = tx.commit(token)
        except (TransbankError, requests.RequestException) as error:
            registro.error("Falló el commit Webpay del pago %s: %r", pago.buy_order, error)
            pago.estado = EstadoPago.ERROR
            pago.respuesta_cruda = {**pago.respuesta_cruda, "error_commit": repr(error)}
            pago.save()
            return pago

        _copiar_datos(pago, respuesta)
        aprobado = respuesta.get("status") == "AUTHORIZED" and respuesta.get("response_code") == 0
        if not aprobado:
            pago.estado = EstadoPago.RECHAZADO
            pago.save()
            return pago

        # Defensa: el monto cobrado debe ser el que la tienda calculó.
        cobrado = respuesta.get("amount")
        if cobrado != pago.monto:
            return _reembolsar(pago, tx, cobrado, f"El monto cobrado (${cobrado}) no coincide con el de la orden (${pago.monto}).")

        try:
            with transaction.atomic():  # savepoint: si falla, solo se revierte este bloque
                pagar_matricula(
                    pago.matricula, usuario, f"Pago aprobado con Webpay Plus (orden {pago.buy_order})."[:255]
                )
        except Exception as error:  # noqa: BLE001 - cualquier fallo obliga a devolver el dinero
            motivo = error.mensaje if isinstance(error, ErrorDeNegocio) else "Error inesperado al registrar la matrícula."
            if not isinstance(error, ErrorDeNegocio):
                registro.exception("Error inesperado al pagar la matrícula %s", pago.matricula_id)
            return _reembolsar(pago, tx, pago.monto, motivo)

        pago.estado = EstadoPago.APROBADO
        pago.save()
        return pago


def _copiar_datos(pago, respuesta):
    """Copia a la fila los datos útiles de la respuesta del commit."""
    pago.response_code = respuesta.get("response_code")
    pago.authorization_code = str(respuesta.get("authorization_code") or "")[:10]
    pago.payment_type_code = str(respuesta.get("payment_type_code") or "")[:5]
    pago.card_number = str((respuesta.get("card_detail") or {}).get("card_number") or "")[-4:]
    pago.respuesta_cruda = {**pago.respuesta_cruda, "commit": respuesta}


# ============================================================
# REEMBOLSO AUTOMÁTICO
# Transbank cobró pero no podemos entregar la matrícula: se devuelve
# el total. Si el refund también falla, el pago queda en ERROR con
# la marca "reembolso_pendiente" para resolverlo a mano; nunca se
# oculta ni se marca como aprobado.
# ============================================================
def _reembolsar(pago, tx, monto, motivo):
    try:
        resultado = tx.refund(pago.token, monto)
    except (TransbankError, requests.RequestException) as error:
        registro.critical("REEMBOLSO PENDIENTE del pago %s (%s): %r", pago.buy_order, motivo, error)
        pago.estado = EstadoPago.ERROR
        pago.respuesta_cruda = {**pago.respuesta_cruda, "motivo": motivo, "reembolso_pendiente": repr(error)}
    else:
        pago.estado = EstadoPago.REEMBOLSADO
        pago.respuesta_cruda = {**pago.respuesta_cruda, "motivo": motivo, "refund": resultado}
    pago.save()
    return pago


# ============================================================
# CIERRES SIN COBRO: ANULADO POR EL USUARIO, EXPIRADO, ERROR DE FORMULARIO
# Solo cambian pagos que siguen INICIADO (idempotente).
# ============================================================
def _cerrar_sin_cobro(filtro, estado, motivo):
    with transaction.atomic():
        pago = PagoWebpay.objects.select_for_update().filter(**filtro).first()
        if pago is None:
            raise PagoNoEncontradoError()
        if pago.estado == EstadoPago.INICIADO:
            pago.estado = estado
            pago.respuesta_cruda = {**pago.respuesta_cruda, "motivo": motivo}
            pago.save()
        return pago


# ============================================================
# RETORNO DESDE WEBPAY: LOS 4 CASOS DE WEBPAY PLUS
#  1) Normal:      token_ws
#  2) Anulado:     TBK_TOKEN + TBK_ORDEN_COMPRA + TBK_ID_SESION
#  3) Timeout:     solo TBK_ORDEN_COMPRA + TBK_ID_SESION
#  4) Error form.: token_ws + TBK_TOKEN
# Devuelve el PagoWebpay resultante, o None si faltan parámetros.
# ============================================================
def procesar_retorno(parametros, usuario=None):
    """Interpreta los parámetros de retorno de Webpay y actúa según el caso."""
    token_ws = parametros.get("token_ws")
    tbk_token = parametros.get("TBK_TOKEN")
    orden = parametros.get("TBK_ORDEN_COMPRA")

    if token_ws and tbk_token:
        return _cerrar_sin_cobro(
            {"token": token_ws}, EstadoPago.ERROR, "Error en el formulario de pago de Webpay."
        )
    if token_ws:
        return confirmar_pago_webpay(token_ws, usuario)
    if tbk_token:
        return _cerrar_sin_cobro(
            {"token": tbk_token}, EstadoPago.ANULADO_POR_USUARIO, "El usuario anuló el pago en Webpay."
        )
    if orden:
        return _cerrar_sin_cobro(
            {"buy_order": orden}, EstadoPago.EXPIRADO, "Se agotó el tiempo para pagar en Webpay."
        )
    return None
