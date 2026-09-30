# ============================================================
# ACADEMIA_BOOTCAMPS/URLS.PY / ENRUTADOR PRINCIPAL
# Orden importante:
#   1) páginas HTML (inicio, oferta, panel, documentación)
#   2) API REST, esquema OpenAPI, Swagger y ReDoc
#   3) archivos estáticos / media
#   4) catch-all re_path(r"^.*$") -> pantalla de redirección
# Con handler404 y el middleware, ninguna ruta muestra el 404 de Django.
# ============================================================
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from carro import urls as carro_urls
from core import views as core_views
from cursos import urls as cursos_urls
from matriculas import urls as matriculas_urls
from usuarios import urls as usuarios_urls

# ============================================================
# 1) PÁGINAS HTML
# ============================================================
urlpatterns = [
    path("", core_views.inicio, name="inicio"),
    path("documentacion/", core_views.documentacion, name="documentacion"),
    path("no-encontrado/", core_views.no_encontrado, name="no_encontrado"),
    path("cursos/", include(cursos_urls.urlpatterns_publico)),
    path("panel/", core_views.panel, name="panel"),
    path(
        "panel/",
        include(
            cursos_urls.urlpatterns_html
            + usuarios_urls.urlpatterns_html
            + carro_urls.urlpatterns_html
            + matriculas_urls.urlpatterns_html
        ),
    ),
    path("admin/", admin.site.urls),
]

# ============================================================
# 2) API REST Y DOCUMENTACIÓN OPENAPI
# ============================================================
urlpatterns += [
    path("api/", core_views.api_raiz, name="api_raiz"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path(
        "api/",
        include(
            usuarios_urls.urlpatterns_api
            + cursos_urls.urlpatterns_api
            + carro_urls.urlpatterns_api
            + matriculas_urls.urlpatterns_api
        ),
    ),
]

# ============================================================
# 3) ESTÁTICOS Y MEDIA (solo en desarrollo)
# ============================================================
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ============================================================
# 4) CATCH-ALL: CUALQUIER OTRA RUTA -> REDIRECCIÓN AL INICIO
# Debe ir al final. Si la ruta existe con barra final, redirige ahí.
# ============================================================
urlpatterns += [re_path(r"^.*$", core_views.redireccion_inicio, name="redireccion")]

handler404 = "core.views.pagina_no_encontrada"
