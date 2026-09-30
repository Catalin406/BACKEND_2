# ============================================================
# USUARIOS/VIEWS.PY / API DE AUTENTICACIÓN Y ADMINISTRACIÓN DE USUARIOS
#   POST /api/auth/registro/  público (siempre ESTUDIANTE)
#   POST /api/auth/login/     LoginConRolView: tokens con claim "rol"
#   POST /api/auth/refresh/   renueva el access (rota el refresh)
#   POST /api/auth/logout/    blacklist del refresh
#   GET  /api/auth/perfil/    datos del usuario + claims del token
#   /api/usuarios/            CRUD del coordinador (baja lógica)
# ============================================================
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from carro.serializers import CarroSerializer
from carro.servicios import obtener_carro
from core.excepciones import ErrorDeNegocio
from core.mixins import BajaLogicaMixin

from .models import Usuario
from .permisos import EsCoordinador
from .serializers import LogoutSerializer, PerfilSerializer, RegistroSerializer, UsuarioSerializer
from .tokens import TokenConRolSerializer

RESPUESTA_ERROR = OpenApiResponse(description="Error en formato {error, mensaje, detalle}.")


# ============================================================
# REGISTRO PÚBLICO
# ============================================================
@extend_schema(tags=["Autenticación"], summary="Registrar una cuenta de estudiante (público)")
class RegistroView(generics.CreateAPIView):
    """Crea un usuario con rol ESTUDIANTE (su carro se crea por señal)."""

    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


# ============================================================
# LOGIN CON CLAIMS DE ROL
# ============================================================
@extend_schema(
    tags=["Autenticación"],
    summary="Iniciar sesión: devuelve access, refresh, rol y usuario",
    examples=[
        OpenApiExample("Login coordinador", request_only=True,
                       value={"username": "coordinador", "password": "Coordinador2026!"}),
        OpenApiExample("Login estudiante", request_only=True,
                       value={"username": "estudiante1", "password": "Estudiante2026!"}),
        OpenApiExample(
            "Respuesta del login", response_only=True, status_codes=["200"],
            value={"access": "eyJhbGciOiJIUzI1NiIs...", "refresh": "eyJhbGciOiJIUzI1NiIs...",
                   "rol": "ESTUDIANTE",
                   "usuario": {"id": 2, "username": "estudiante1", "email": "estudiante1@codelab.cl",
                               "nombre_completo": "Valentina Rojas", "rol": "ESTUDIANTE",
                               "rol_display": "Estudiante"}},
        ),
    ],
)
class LoginConRolView(TokenObtainPairView):
    """Login JWT que usa TokenConRolSerializer."""

    serializer_class = TokenConRolSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema(tags=["Autenticación"], summary="Renovar el access token con el refresh")
class RefrescarTokenView(TokenRefreshView):
    """Rota el refresh y emite un nuevo access."""

    permission_classes = [AllowAny]
    authentication_classes = []


# ============================================================
# LOGOUT (BLACKLIST)
# ============================================================
class LogoutView(APIView):
    """Invalida el refresh token. El carro NO se toca: vive en la BD."""

    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        tags=["Autenticación"],
        summary="Cerrar sesión: el refresh queda en la blacklist",
        request=LogoutSerializer,
        responses={200: OpenApiResponse(description="Sesión cerrada."), 400: RESPUESTA_ERROR},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"mensaje": "Sesión cerrada. El refresh token fue invalidado."}, status=status.HTTP_200_OK)


# ============================================================
# PERFIL + CLAIMS DEL TOKEN
# ============================================================
class PerfilView(APIView):
    """Datos del usuario autenticado y los claims leídos de request.auth."""

    permission_classes = [IsAuthenticated]
    serializer_class = PerfilSerializer

    @extend_schema(tags=["Autenticación"], summary="Ver mi perfil y los claims de mi token")
    def get(self, request):
        claims = {
            clave: request.auth.get(clave)
            for clave in ("user_id", "rol", "username", "email", "nombre_completo", "exp", "iat", "jti")
        }
        return Response({"usuario": PerfilSerializer(request.user).data, "claims_token": claims})


# ============================================================
# CRUD DE USUARIOS (COORDINADOR)
# DELETE = is_active=False. /carro-matricula/ muestra el carro
# persistido de cualquier estudiante.
# ============================================================
@extend_schema_view(
    list=extend_schema(tags=["Usuarios"], summary="Listar usuarios (coordinador)"),
    retrieve=extend_schema(tags=["Usuarios"], summary="Ver usuario (coordinador)"),
    create=extend_schema(tags=["Usuarios"], summary="Crear usuario con rol (coordinador)"),
    update=extend_schema(tags=["Usuarios"], summary="Reemplazar usuario (coordinador)"),
    partial_update=extend_schema(tags=["Usuarios"], summary="Editar usuario (coordinador)"),
    destroy=extend_schema(tags=["Usuarios"], summary="Desactivar usuario: is_active=False (coordinador)"),
    reactivar=extend_schema(tags=["Usuarios"], summary="Reactivar usuario (coordinador)", request=None),
    carro_matricula=extend_schema(tags=["Usuarios"], summary="Ver el carro de un estudiante (coordinador)",
                                  responses={200: CarroSerializer}),
)
class UsuarioViewSet(BajaLogicaMixin, viewsets.ModelViewSet):
    """Administración de usuarios por el coordinador."""

    serializer_class = UsuarioSerializer
    permission_classes = [EsCoordinador]
    filterset_fields = ["rol", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name", "rut"]
    ordering_fields = ["username", "date_joined"]
    ordering = ["username"]
    campo_activo = "is_active"
    nombre_recurso = "usuario"

    def get_queryset(self):
        return Usuario.objects.all()

    def destroy(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            raise ErrorDeNegocio("No puedes desactivar tu propia cuenta.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="carro-matricula")
    def carro_matricula(self, request, pk=None):
        usuario = self.get_object()
        return Response(CarroSerializer(obtener_carro(usuario)).data)
