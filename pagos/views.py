# ============================================================
# PAGOS/VIEWS.PY / API PARA INICIAR EL PAGO CON WEBPAY (ESTUDIANTE)
#   POST /api/matriculas/webpay/iniciar/          desde el carro
#   POST /api/matriculas/{id}/webpay/iniciar/     matrícula PENDIENTE propia
# Ambos devuelven {url, token}: el cliente envía un formulario POST
# con el campo token_ws a esa url. La lógica está en pagos/servicios.py.
# ============================================================
from django.urls import reverse
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from matriculas.models import Matricula
from matriculas.servicios import crear_matricula_pendiente
from usuarios.permisos import EsEstudiante, EsPropietarioDeLaMatricula

from . import servicios
from .serializers import IniciarPagoRespuestaSerializer

RESPUESTA_ERROR = OpenApiResponse(description="Error en formato {error, mensaje, detalle}.")

EJEMPLO_OK = OpenApiExample(
    "Pago iniciado (201)",
    response_only=True,
    status_codes=["201"],
    value={
        "mensaje": "Pago iniciado. Envía un formulario POST con token_ws a la url indicada.",
        "matricula_id": 12,
        "monto": 349990,
        "buy_order": "M12-3f1c9a528a0e",
        "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
        "token": "01ab23cd45ef67ab89cd01ef23ab45cd67ef89ab01cd23ef45ab67cd89ef01ab",
    },
)


def _responder(request, matricula):
    """Inicia el pago y arma la respuesta común de ambos endpoints."""
    return_url = request.build_absolute_uri(reverse("pagos_webpay_retorno"))
    pago, url = servicios.iniciar_pago_webpay(matricula, return_url)
    return Response(
        {
            "mensaje": "Pago iniciado. Envía un formulario POST con token_ws a la url indicada.",
            "matricula_id": matricula.pk,
            "monto": pago.monto,
            "buy_order": pago.buy_order,
            "url": url,
            "token": pago.token,
        },
        status=status.HTTP_201_CREATED,
    )


# ============================================================
# DESDE EL CARRO: crea (o reutiliza) la matrícula PENDIENTE
# ============================================================
class IniciarWebpayCarroView(APIView):
    """Convierte el carro en matrícula PENDIENTE e inicia su pago."""

    permission_classes = [EsEstudiante]
    serializer_class = IniciarPagoRespuestaSerializer

    @extend_schema(
        tags=["Pagos Webpay"],
        operation_id="matriculas_webpay_iniciar_carro",
        summary="Pagar el carro con Webpay Plus: crea (o reutiliza) la matrícula PENDIENTE e inicia el pago (estudiante)",
        request=None,
        responses={201: IniciarPagoRespuestaSerializer, 400: RESPUESTA_ERROR, 409: RESPUESTA_ERROR, 502: RESPUESTA_ERROR},
        examples=[EJEMPLO_OK],
    )
    def post(self, request):
        matricula = crear_matricula_pendiente(request.user)
        return _responder(request, matricula)


# ============================================================
# DESDE UNA MATRÍCULA PENDIENTE PROPIA
# El permiso de objeto devuelve 403 si la matrícula es ajena.
# ============================================================
class IniciarWebpayMatriculaView(APIView):
    """Inicia el pago de una matrícula PENDIENTE del estudiante."""

    permission_classes = [EsEstudiante, EsPropietarioDeLaMatricula]
    serializer_class = IniciarPagoRespuestaSerializer

    @extend_schema(
        tags=["Pagos Webpay"],
        operation_id="matriculas_webpay_iniciar_matricula",
        summary="Iniciar el pago Webpay de una matrícula PENDIENTE propia (estudiante)",
        request=None,
        responses={
            201: IniciarPagoRespuestaSerializer, 403: RESPUESTA_ERROR, 404: RESPUESTA_ERROR,
            409: RESPUESTA_ERROR, 502: RESPUESTA_ERROR,
        },
        examples=[EJEMPLO_OK],
    )
    def post(self, request, pk):
        matricula = Matricula.objects.filter(pk=pk).first()
        if matricula is None:
            raise NotFound()
        self.check_object_permissions(request, matricula)
        return _responder(request, matricula)
