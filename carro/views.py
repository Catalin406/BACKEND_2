# ============================================================
# CARRO/VIEWS.PY / API DEL CARRO DE MATRÍCULA (SOLO ESTUDIANTE)
#   GET    /api/carro-matricula/                   ver carro
#   POST   /api/carro-matricula/                   agregar curso
#   DELETE /api/carro-matricula/                   vaciar carro
#   DELETE /api/carro-matricula/items/{curso_id}/  quitar curso
# Toda la lógica vive en carro/servicios.py.
# ============================================================
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permisos import EsEstudiante

from . import servicios
from .serializers import AgregarCursoSerializer, CarroSerializer

RESPUESTA_ERROR = OpenApiResponse(description="Error en formato {error, mensaje, detalle}.")


class CarroMatriculaView(APIView):
    """Carro persistente del estudiante autenticado."""

    permission_classes = [EsEstudiante]
    serializer_class = CarroSerializer

    def _respuesta_carro(self, request, codigo=status.HTTP_200_OK, mensaje=None):
        carro = servicios.obtener_carro(request.user)
        datos = CarroSerializer(carro).data
        if mensaje:
            datos = {"mensaje": mensaje, **datos}
        return Response(datos, status=codigo)

    # ============================================================
    # VER CARRO
    # ============================================================
    @extend_schema(tags=["Carro de matrícula"], summary="Ver mi carro de matrícula (estudiante)",
                   responses={200: CarroSerializer, 401: RESPUESTA_ERROR, 403: RESPUESTA_ERROR})
    def get(self, request):
        return self._respuesta_carro(request)

    # ============================================================
    # AGREGAR CURSO
    # ============================================================
    @extend_schema(
        tags=["Carro de matrícula"],
        summary="Agregar un curso al carro (estudiante)",
        request=AgregarCursoSerializer,
        responses={201: CarroSerializer, 400: RESPUESTA_ERROR, 409: RESPUESTA_ERROR},
        examples=[
            OpenApiExample("Agregar un curso", value={"curso": 1}, request_only=True),
            OpenApiExample(
                "Curso duplicado (400)",
                response_only=True,
                status_codes=["400"],
                value={
                    "error": True,
                    "mensaje": "Este curso ya está en tu carro de matrícula.",
                    "detalle": {"curso_id": 1, "titulo": "Bootcamp Full Stack Python"},
                },
            ),
        ],
    )
    def post(self, request):
        entrada = AgregarCursoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        item = servicios.agregar_curso(request.user, entrada.validated_data["curso"])
        return self._respuesta_carro(
            request, status.HTTP_201_CREATED, f"Curso «{item.curso.titulo}» agregado al carro."
        )

    # ============================================================
    # VACIAR CARRO
    # ============================================================
    @extend_schema(tags=["Carro de matrícula"], summary="Vaciar el carro (estudiante)",
                   responses={200: CarroSerializer})
    def delete(self, request):
        cantidad = servicios.vaciar_carro(request.user)
        return self._respuesta_carro(request, mensaje=f"Carro vaciado ({cantidad} cursos quitados).")


class QuitarCursoCarroView(APIView):
    """Quita un curso del carro (baja lógica del ítem)."""

    permission_classes = [EsEstudiante]
    serializer_class = CarroSerializer

    @extend_schema(tags=["Carro de matrícula"], summary="Quitar un curso del carro (estudiante)",
                   responses={200: CarroSerializer, 404: RESPUESTA_ERROR})
    def delete(self, request, curso_id):
        servicios.quitar_curso(request.user, curso_id)
        carro = servicios.obtener_carro(request.user)
        return Response({"mensaje": "Curso quitado del carro.", **CarroSerializer(carro).data})
