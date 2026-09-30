# ============================================================
# CURSOS/URLS.PY / RUTAS DE ÁREAS Y CURSOS
# urlpatterns_api -> /api/ ; urlpatterns_publico -> /cursos/ ;
# urlpatterns_html -> /panel/ (gestión del coordinador).
# ============================================================
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views, views_html

router = DefaultRouter()
router.include_root_view = False
router.register("areas", views.AreaViewSet, basename="areas")
router.register("cursos", views.CursoViewSet, basename="cursos")

urlpatterns_api = [path("", include(router.urls))]

urlpatterns_publico = [
    path("", views_html.oferta_lista, name="oferta_lista"),
    path("<int:pk>/", views_html.oferta_detalle, name="oferta_detalle"),
]

urlpatterns_html = [
    # Áreas
    path("areas/", views_html.area_lista, name="panel_areas"),
    path("areas/nueva/", views_html.area_crear, name="panel_area_crear"),
    path("areas/<int:pk>/", views_html.area_detalle, name="panel_area_detalle"),
    path("areas/<int:pk>/editar/", views_html.area_editar, name="panel_area_editar"),
    path("areas/<int:pk>/desactivar/", views_html.area_desactivar, name="panel_area_desactivar"),
    path("areas/<int:pk>/reactivar/", views_html.area_reactivar, name="panel_area_reactivar"),
    # Cursos
    path("cursos/", views_html.curso_lista, name="panel_cursos"),
    path("cursos/nuevo/", views_html.curso_crear, name="panel_curso_crear"),
    path("cursos/<int:pk>/", views_html.curso_detalle, name="panel_curso_detalle"),
    path("cursos/<int:pk>/editar/", views_html.curso_editar, name="panel_curso_editar"),
    path("cursos/<int:pk>/desactivar/", views_html.curso_desactivar, name="panel_curso_desactivar"),
    path("cursos/<int:pk>/reactivar/", views_html.curso_reactivar, name="panel_curso_reactivar"),
]
