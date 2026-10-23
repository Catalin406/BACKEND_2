# ============================================================
# CORE/VIEWS.PY / INICIO, PANEL, DOCUMENTACIÓN, RAÍZ DE LA API
# Y CONTROL DE RUTAS INEXISTENTES
# Las rutas que no existen nunca muestran el 404 de Django: terminan
# en la pantalla core/redireccion.html, que vuelve al inicio en 3 s.
# ============================================================
from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render
from django.urls import Resolver404, resolve
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from cursos.models import AreaConocimiento, Curso
from matriculas.models import EstadoMatricula, Inscripcion, Matricula
from usuarios.models import Rol, Usuario


# ============================================================
# INICIO: PORTADA CON ESTADÍSTICAS REALES
# ============================================================
def inicio(request):
    """Portada con estadísticas de la BD y próximos cursos."""
    cursos_activos = Curso.objects.filter(activo=True, area__activo=True)
    por_estado = dict(Matricula.objects.values_list("estado").annotate(n=Count("id")))
    estadisticas_matriculas = [
        {"valor": valor, "etiqueta": etiqueta, "cantidad": por_estado.get(valor, 0)}
        for valor, etiqueta in EstadoMatricula.choices
    ]
    contexto = {
        "total_cursos": cursos_activos.count(),
        "total_areas": AreaConocimiento.objects.filter(activo=True).count(),
        "total_cupos": cursos_activos.aggregate(t=Sum("cupos_disponibles"))["t"] or 0,
        "total_inscripciones": Inscripcion.objects.filter(activa=True).count(),
        "estadisticas_matriculas": estadisticas_matriculas,
        "proximos_cursos": cursos_activos.filter(fecha_inicio__gte=timezone.localdate())
        .select_related("area")
        .order_by("fecha_inicio")[:6],
        "areas": AreaConocimiento.objects.filter(activo=True).annotate(
            n_cursos=Count("cursos", filter=Q(cursos__activo=True))
        ),
    }
    return render(request, "core/inicio.html", contexto)


# ============================================================
# PANEL DE GESTIÓN
# ============================================================
def panel(request):
    """Tarjetas de acceso a cada módulo con sus contadores."""
    contexto = {
        "n_areas": AreaConocimiento.objects.filter(activo=True).count(),
        "n_cursos": Curso.objects.filter(activo=True).count(),
        "n_usuarios": Usuario.objects.filter(is_active=True).count(),
        "n_estudiantes": Usuario.objects.filter(is_active=True, rol=Rol.ESTUDIANTE).count(),
        "n_matriculas": Matricula.objects.count(),
        "n_pagadas": Matricula.objects.filter(estado=EstadoMatricula.PAGADO).count(),
        "n_inscripciones": Inscripcion.objects.filter(activa=True).count(),
    }
    return render(request, "core/panel.html", contexto)


# ============================================================
# DOCUMENTACIÓN DEL SISTEMA
# ============================================================
def documentacion(request):
    """Guía del sistema con enlaces a Swagger y ReDoc."""
    return render(request, "core/documentacion.html", {"estados": EstadoMatricula.choices})


# ============================================================
# RAÍZ DE LA API (PÚBLICA)
# ============================================================
@extend_schema(tags=["General"], summary="Raíz de la API: proyecto, alumna y endpoints",
               responses={200: OpenApiResponse(description="Información general de la API.")})
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def api_raiz(request):
    """Nombre del proyecto, datos de la alumna y lista de endpoints."""
    base = request.build_absolute_uri("/api/")
    return Response({
        "proyecto": settings.NOMBRE_COMERCIAL,
        "descripcion": "API REST de matrículas para cursos, bootcamps y talleres.",
        "alumna": {
            "nombre": settings.ALUMNO_NOMBRE,
            "seccion": settings.ALUMNO_SECCION,
            "anio": settings.ALUMNO_ANIO,
        },
        "documentacion": {"swagger": f"{base}docs/", "redoc": f"{base}redoc/", "schema": f"{base}schema/"},
        "endpoints": {
            "publico": ["GET /api/cursos/", "GET /api/cursos/{id}/", "GET /api/areas/", "GET /api/areas/{id}/",
                        "POST /api/auth/registro/", "POST /api/auth/login/", "POST /api/auth/refresh/"],
            "autenticado": ["POST /api/auth/logout/", "GET /api/auth/perfil/"],
            "estudiante": ["GET/POST/DELETE /api/carro-matricula/", "DELETE /api/carro-matricula/items/{curso_id}/",
                           "POST /api/matriculas/confirmar/", "POST /api/matriculas/webpay/iniciar/",
                           "POST /api/matriculas/{id}/webpay/iniciar/", "GET /api/mis-matriculas/",
                           "GET /api/mis-matriculas/{id}/"],
            "coordinador": ["POST/PUT/PATCH/DELETE /api/cursos/", "POST /api/cursos/{id}/reactivar/",
                            "POST/PUT/PATCH/DELETE /api/areas/", "POST /api/areas/{id}/reactivar/",
                            "GET /api/matriculas/", "GET /api/matriculas/{id}/",
                            "PATCH /api/matriculas/{id}/estado/", "GET /api/inscripciones/",
                            "CRUD /api/usuarios/", "POST /api/usuarios/{id}/reactivar/",
                            "GET /api/usuarios/{id}/carro-matricula/"],
        },
    })


# ============================================================
# PANTALLA DE REDIRECCIÓN (RUTAS INEXISTENTES)
# Se responde con 200 y la plantilla redirige al inicio en 3 s
# (meta refresh + respaldo en JavaScript).
# ============================================================
def renderizar_redireccion(request, ruta=None):
    """Renderiza core/redireccion.html con la ruta solicitada."""
    return render(request, "core/redireccion.html", {"ruta_solicitada": ruta or request.path, "segundos": 3})


def _existe_con_barra(ruta):
    """True si ruta + '/' resuelve a una vista real (no al catch-all)."""
    try:
        coincidencia = resolve(ruta + "/")
    except Resolver404:
        return False
    return coincidencia.url_name != "redireccion"


def redireccion_inicio(request):
    """Catch-all: completa la barra final si corresponde o muestra la redirección."""
    if not request.path.endswith("/") and _existe_con_barra(request.path):
        destino = request.path + "/"
        if request.META.get("QUERY_STRING"):
            destino += "?" + request.META["QUERY_STRING"]
        return HttpResponsePermanentRedirect(destino)
    return renderizar_redireccion(request)


def no_encontrado(request):
    """Destino de obtener_o_redirigir(): muestra el aviso con la ruta original."""
    return renderizar_redireccion(request, request.GET.get("ruta") or request.path)


def pagina_no_encontrada(request, exception=None):
    """handler404: con DEBUG=False cualquier 404 muestra la redirección."""
    return renderizar_redireccion(request)
