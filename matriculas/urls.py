# ============================================================
# MATRICULAS/URLS.PY / RUTAS DE MATRÍCULAS E INSCRIPCIONES
# "matriculas/confirmar/" va ANTES del router para que no la capture
# la ruta de detalle /matriculas/{id}/.
# ============================================================
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views, views_html

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("mis-matriculas", views.MisMatriculasViewSet, basename="mis-matriculas")
router.register("matriculas", views.MatriculaViewSet, basename="matriculas")
router.register("inscripciones", views.InscripcionViewSet, basename="inscripciones")

urlpatterns_api = [
    path("matriculas/confirmar/", views.ConfirmarMatriculaView.as_view(), name="api_confirmar_matricula"),
    path("", include(router.urls)),
]

urlpatterns_html = [
    path("matriculas/", views_html.matricula_lista, name="panel_matriculas"),
    path("matriculas/<int:pk>/", views_html.matricula_detalle, name="panel_matricula_detalle"),
    path("matriculas/<int:pk>/estado/", views_html.matricula_cambiar_estado, name="panel_matricula_estado"),
    path("inscripciones/", views_html.inscripcion_lista, name="panel_inscripciones"),
]
