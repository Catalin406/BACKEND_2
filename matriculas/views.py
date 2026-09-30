# ============================================================
# MATRICULAS/VIEWS.PY / API DE MATRÍCULAS E INSCRIPCIONES
#   POST  /api/matriculas/confirmar/        estudiante: checkout
#   GET   /api/mis-matriculas/[{id}/]       estudiante: solo las suyas
#   GET   /api/matriculas/[{id}/]           coordinador: todas, con filtros
#   PATCH /api/matriculas/{id}/estado/      coordinador: cambiar estado
#   GET   /api/inscripciones/               coordinador: inscritos por curso
# La lógica está en matriculas/servicios.py.
# ============================================================
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permisos import EsCoordinador, EsEstudiante, EsPropietarioDeLaMatricula

from . import servicios
from .filtros import InscripcionFilter, MatriculaFilter
from .models import Inscripcion, Matricula
from .serializers import CambioEstadoSerializer, InscripcionSerializer, MatriculaSerializer

RESPUESTA_ERROR = OpenApiResponse(description="Error en formato {error, mensaje, detalle}.")


def queryset_matriculas():
    """Matrículas con total anotado y relaciones precargadas."""
    return (
        Matricula.objects.con_total()
        .select_related("estudiante")
        .prefetch_related("detalles__curso__area", "detalles__inscripcion", "historial__cambiado_por")
    )


# ============================================================
# CONFIRMAR MATRÍCULA (ESTUDIANTE)
# ============================================================
class ConfirmarMatriculaView(APIView):
    """Checkout: convierte el carro en una matrícula PAGADA."""

    permission_classes = [EsEstudiante]
    serializer_class = MatriculaSerializer

    @extend_schema(
        tags=["Matrículas"],
        summary="Confirmar matrícula: pago simulado, descuento de cupos e inscripciones UUID (estudiante)",
        request=None,
        responses={201: MatriculaSerializer, 400: RESPUESTA_ERROR, 409: RESPUESTA_ERROR},
        examples=[
            OpenApiExample(
                "Matrícula confirmada (201)",
                response_only=True,
                status_codes=["201"],
                value={
                    "mensaje": "Matrícula confirmada y pagada. Se emitieron 1 inscripciones.",
                    "id": 12,
                    "codigo": "3f1c9a52-8a0e-4c1e-9d8a-5c2b7f0e4b11",
                    "estado": "PAGADO",
                    "total": "349990",
                    "detalles": [
                        {"curso_titulo": "Taller de Git y GitHub", "costo_matricula": "349990",
                         "inscripcion": {"codigo": "a8b0f1d2-6c3e-4b7a-9f10-2d3e4f5a6b7c", "activa": True}}
                    ],
                },
            ),
            OpenApiExample(
                "Sin cupos (409)",
                response_only=True,
                status_codes=["409"],
                value={
                    "error": True,
                    "mensaje": "No hay cupos disponibles en: «Bootcamp Ciberseguridad Ofensiva». "
                               "Quita esos cursos del carro para continuar.",
                    "detalle": {"cursos_sin_cupo": [
                        {"curso_id": 7, "titulo": "Bootcamp Ciberseguridad Ofensiva", "cupos_disponibles": 0}
                    ]},
                },
            ),
        ],
    )
    def post(self, request):
        matricula = servicios.confirmar_matricula(request.user)
        datos = MatriculaSerializer(queryset_matriculas().get(pk=matricula.pk)).data
        cantidad = len(datos["detalles"])
        return Response(
            {"mensaje": f"Matrícula confirmada y pagada. Se emitieron {cantidad} inscripciones.", **datos},
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# MIS MATRÍCULAS (ESTUDIANTE)
# El queryset filtra por el usuario del token y además se aplica
# el permiso de objeto EsPropietarioDeLaMatricula.
# ============================================================
@extend_schema_view(
    list=extend_schema(tags=["Matrículas"], summary="Mis matrículas (estudiante)"),
    retrieve=extend_schema(tags=["Matrículas"], summary="Detalle de una de mis matrículas (estudiante)"),
)
class MisMatriculasViewSet(viewsets.ReadOnlyModelViewSet):
    """Matrículas del estudiante autenticado."""

    serializer_class = MatriculaSerializer
    permission_classes = [EsEstudiante, EsPropietarioDeLaMatricula]
    filterset_fields = ["estado"]
    ordering_fields = ["creada_en"]
    ordering = ["-creada_en"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Matricula.objects.none()
        return queryset_matriculas().filter(estudiante=self.request.user)


# ============================================================
# MATRÍCULAS (COORDINADOR)
# ============================================================
@extend_schema_view(
    list=extend_schema(tags=["Matrículas"], summary="Listar matrículas con filtros (coordinador)"),
    retrieve=extend_schema(tags=["Matrículas"], summary="Detalle de matrícula con inscripciones e historial (coordinador)"),
)
class MatriculaViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de todas las matrículas y cambio de estado."""

    serializer_class = MatriculaSerializer
    permission_classes = [EsCoordinador]
    filterset_class = MatriculaFilter
    search_fields = ["codigo", "estudiante__username", "estudiante__email"]
    ordering_fields = ["creada_en", "pagada_en", "estado"]
    ordering = ["-creada_en"]

    def get_queryset(self):
        return queryset_matriculas()

    @extend_schema(
        tags=["Matrículas"],
        summary="Cambiar estado de una matrícula (coordinador)",
        request=CambioEstadoSerializer,
        responses={200: MatriculaSerializer, 400: RESPUESTA_ERROR, 403: RESPUESTA_ERROR},
        examples=[
            OpenApiExample("Cancelar (libera cupos)", request_only=True,
                           value={"estado": "CANCELADO", "observacion": "Solicitud del estudiante."}),
            OpenApiExample("Marcar completada", request_only=True,
                           value={"estado": "COMPLETADO", "observacion": "Curso finalizado."}),
            OpenApiExample(
                "Transición inválida (400)", response_only=True, status_codes=["400"],
                value={"error": True,
                       "mensaje": "No se puede cambiar una matrícula de Cancelado a Pagado. Cancelado es un estado final.",
                       "detalle": {"estado_actual": "CANCELADO", "estado_solicitado": "PAGADO", "permitidos": []}},
            ),
        ],
    )
    @action(detail=True, methods=["patch"], url_path="estado")
    def estado(self, request, pk=None):
        matricula = self.get_object()
        entrada = CambioEstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        servicios.cambiar_estado_matricula(
            matricula, entrada.validated_data["estado"], request.user, entrada.validated_data["observacion"]
        )
        datos = MatriculaSerializer(queryset_matriculas().get(pk=matricula.pk)).data
        return Response({"mensaje": f"Estado actualizado a {datos['estado_display']}.", **datos})


# ============================================================
# INSCRIPCIONES OFICIALES (COORDINADOR)
# ============================================================
@extend_schema_view(
    list=extend_schema(tags=["Matrículas"], summary="Inscripciones oficiales por curso (coordinador)"),
    retrieve=extend_schema(tags=["Matrículas"], summary="Ver una inscripción (coordinador)"),
)
class InscripcionViewSet(viewsets.ReadOnlyModelViewSet):
    """Inscritos por curso, filtrables por curso y activa."""

    serializer_class = InscripcionSerializer
    permission_classes = [EsCoordinador]
    filterset_class = InscripcionFilter
    search_fields = ["codigo", "detalle__matricula__estudiante__username", "detalle__curso__titulo"]
    ordering_fields = ["emitida_en"]
    ordering = ["-emitida_en"]

    def get_queryset(self):
        return Inscripcion.objects.select_related("detalle__curso", "detalle__matricula__estudiante")
