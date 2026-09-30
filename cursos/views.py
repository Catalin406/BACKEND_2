# ============================================================
# CURSOS/VIEWS.PY / API DE LA OFERTA ACADÉMICA
# AreaViewSet y CursoViewSet: lectura pública (AllowAny implícito en
# EsCoordinadorOSoloLectura) y escritura solo del coordinador.
# DELETE es baja lógica; /reactivar/ vuelve a activar.
# Filtros, búsqueda, orden y paginación en /api/cursos/.
# ============================================================
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.response import Response

from core.mixins import BajaLogicaMixin
from usuarios.permisos import EsCoordinadorOSoloLectura

from .filtros import CursoFilter
from .models import AreaConocimiento, Curso
from .serializers import AreaSerializer, CursoEscrituraSerializer, CursoLecturaSerializer

PARAM_INACTIVOS = OpenApiParameter(
    "incluir_inactivos", OpenApiTypes.BOOL, description="Solo coordinador: incluye registros inactivos."
)
RESPUESTA_BAJA = OpenApiResponse(description="Registro desactivado (baja lógica, no se borra la fila).")

EJEMPLO_CURSO = OpenApiExample(
    "Crear bootcamp",
    request_only=True,
    value={
        "titulo": "Bootcamp Full Stack Python",
        "descripcion": "Django, DRF, PostgreSQL y despliegue en la nube.",
        "area": 1,
        "tipo": "BOOTCAMP",
        "modalidad": "HIBRIDA",
        "costo_matricula": 1490000,
        "fecha_inicio": "2027-03-01",
        "fecha_termino": "2027-06-30",
        "cupos_maximos": 25,
    },
)


# ============================================================
# ÁREAS DE CONOCIMIENTO
# ============================================================
@extend_schema_view(
    list=extend_schema(tags=["Oferta académica"], summary="Listar áreas de conocimiento (público)",
                       parameters=[PARAM_INACTIVOS]),
    retrieve=extend_schema(tags=["Oferta académica"], summary="Ver un área (público)"),
    create=extend_schema(tags=["Oferta académica"], summary="Crear área (coordinador)"),
    update=extend_schema(tags=["Oferta académica"], summary="Reemplazar área (coordinador)"),
    partial_update=extend_schema(tags=["Oferta académica"], summary="Editar área (coordinador)"),
    destroy=extend_schema(tags=["Oferta académica"], summary="Desactivar área: baja lógica (coordinador)",
                          responses={200: RESPUESTA_BAJA}),
    reactivar=extend_schema(tags=["Oferta académica"], summary="Reactivar área (coordinador)", request=None,
                            responses={200: RESPUESTA_BAJA}),
)
class AreaViewSet(BajaLogicaMixin, viewsets.ModelViewSet):
    """CRUD de áreas de conocimiento."""

    serializer_class = AreaSerializer
    permission_classes = [EsCoordinadorOSoloLectura]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["nombre", "creado_en"]
    ordering = ["nombre"]
    filterset_fields = ["activo"]
    nombre_recurso = "área"

    def get_queryset(self):
        return self.filtrar_activos(AreaConocimiento.objects.all())


# ============================================================
# CURSOS / BOOTCAMPS / TALLERES
# ============================================================
@extend_schema_view(
    list=extend_schema(
        tags=["Oferta académica"],
        summary="Listar cursos con filtros, búsqueda, orden y paginación (público)",
        parameters=[
            PARAM_INACTIVOS,
            OpenApiParameter("search", OpenApiTypes.STR, description="Busca en título, descripción y nombre del área."),
            OpenApiParameter(
                "ordering", OpenApiTypes.STR,
                description="costo_matricula, fecha_inicio, titulo o cupos_disponibles (prefijo - para descendente).",
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Oferta académica"], summary="Ver detalle de un curso (público)"),
    create=extend_schema(tags=["Oferta académica"], summary="Crear curso (coordinador)",
                         examples=[EJEMPLO_CURSO], responses={201: CursoLecturaSerializer}),
    update=extend_schema(tags=["Oferta académica"], summary="Reemplazar curso (coordinador)",
                         examples=[EJEMPLO_CURSO], responses={200: CursoLecturaSerializer}),
    partial_update=extend_schema(tags=["Oferta académica"], summary="Editar curso (coordinador)",
                                 responses={200: CursoLecturaSerializer}),
    destroy=extend_schema(tags=["Oferta académica"], summary="Desactivar curso: baja lógica (coordinador)",
                          responses={200: RESPUESTA_BAJA}),
    reactivar=extend_schema(tags=["Oferta académica"], summary="Reactivar curso (coordinador)", request=None,
                            responses={200: RESPUESTA_BAJA}),
)
class CursoViewSet(BajaLogicaMixin, viewsets.ModelViewSet):
    """CRUD de cursos con filtros de django-filter."""

    permission_classes = [EsCoordinadorOSoloLectura]
    filterset_class = CursoFilter
    search_fields = ["titulo", "descripcion", "area__nombre"]
    ordering_fields = ["costo_matricula", "fecha_inicio", "titulo", "cupos_disponibles"]
    ordering = ["fecha_inicio", "titulo"]
    nombre_recurso = "curso"

    def get_queryset(self):
        queryset = Curso.objects.select_related("area")
        if not self.incluir_inactivos():
            queryset = queryset.filter(activo=True, area__activo=True)
        return queryset

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CursoEscrituraSerializer
        return CursoLecturaSerializer

    # ============================================================
    # RESPUESTAS DE ESCRITURA CON EL FORMATO DE LECTURA
    # ============================================================
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        curso = serializer.save()
        return Response(CursoLecturaSerializer(curso).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        curso = self.get_object()
        serializer = self.get_serializer(curso, data=request.data, partial=parcial)
        serializer.is_valid(raise_exception=True)
        curso = serializer.save()
        curso.refresh_from_db()
        return Response(CursoLecturaSerializer(curso).data)
