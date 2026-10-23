# ============================================================
# PAGOS/URLS.PY / RUTAS DE PAGOS WEBPAY
# urlpatterns_api -> /api/ (iniciar pago, estudiante con JWT)
# urlpatterns_panel -> /panel/ (botón "Pagar con Webpay", coordinador)
# urlpatterns_publico -> /pagos/ (retorno de Webpay, sin login)
# ============================================================
from django.urls import path

from . import views, views_html

urlpatterns_api = [
    path("matriculas/webpay/iniciar/", views.IniciarWebpayCarroView.as_view(), name="api_webpay_iniciar_carro"),
    path(
        "matriculas/<int:pk>/webpay/iniciar/",
        views.IniciarWebpayMatriculaView.as_view(),
        name="api_webpay_iniciar_matricula",
    ),
]

urlpatterns_panel = [
    path("matriculas/<int:pk>/pagar-webpay/", views_html.panel_pagar_webpay, name="panel_pagar_webpay"),
]

urlpatterns_publico = [
    path("webpay/retorno/", views_html.webpay_retorno, name="pagos_webpay_retorno"),
]
