# ============================================================
# CARRO/URLS.PY / RUTAS DEL CARRO DE MATRÍCULA
# urlpatterns_api se monta bajo /api/ y urlpatterns_html bajo /panel/.
# ============================================================
from django.urls import path

from . import views, views_html

urlpatterns_api = [
    path("carro-matricula/", views.CarroMatriculaView.as_view(), name="api_carro"),
    path("carro-matricula/items/<int:curso_id>/", views.QuitarCursoCarroView.as_view(), name="api_carro_quitar"),
]

urlpatterns_html = [
    path("carros/", views_html.carro_panel, name="panel_carros"),
    path("carros/<int:estudiante_id>/agregar/", views_html.carro_agregar, name="panel_carro_agregar"),
    path("carros/<int:estudiante_id>/quitar/<int:curso_id>/", views_html.carro_quitar, name="panel_carro_quitar"),
    path("carros/<int:estudiante_id>/vaciar/", views_html.carro_vaciar, name="panel_carro_vaciar"),
    path("carros/<int:estudiante_id>/confirmar/", views_html.carro_confirmar, name="panel_carro_confirmar"),
]
