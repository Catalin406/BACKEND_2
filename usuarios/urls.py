# ============================================================
# USUARIOS/URLS.PY / RUTAS DE AUTENTICACIÓN Y USUARIOS
# urlpatterns_api se monta bajo /api/ y urlpatterns_html bajo /panel/.
# ============================================================
from django.contrib.auth import views as vistas_auth
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views, views_html
from .forms import LoginPanelForm

router = DefaultRouter()
router.include_root_view = False
router.register("usuarios", views.UsuarioViewSet, basename="usuarios")

urlpatterns_api = [
    path("auth/registro/", views.RegistroView.as_view(), name="api_registro"),
    path("auth/login/", views.LoginConRolView.as_view(), name="api_login"),
    path("auth/refresh/", views.RefrescarTokenView.as_view(), name="api_refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="api_logout"),
    path("auth/perfil/", views.PerfilView.as_view(), name="api_perfil"),
    path("", include(router.urls)),
]

urlpatterns_html = [
    # Sesión del panel: el logout es solo POST (Django 5 lo exige).
    path(
        "login/",
        vistas_auth.LoginView.as_view(
            template_name="usuarios/login.html", authentication_form=LoginPanelForm, redirect_authenticated_user=False
        ),
        name="panel_login",
    ),
    path("logout/", vistas_auth.LogoutView.as_view(), name="panel_logout"),
    path("usuarios/", views_html.usuario_lista, name="panel_usuarios"),
    path("usuarios/nuevo/", views_html.usuario_crear, name="panel_usuario_crear"),
    path("usuarios/<int:pk>/", views_html.usuario_detalle, name="panel_usuario_detalle"),
    path("usuarios/<int:pk>/editar/", views_html.usuario_editar, name="panel_usuario_editar"),
    path("usuarios/<int:pk>/desactivar/", views_html.usuario_desactivar, name="panel_usuario_desactivar"),
    path("usuarios/<int:pk>/reactivar/", views_html.usuario_reactivar, name="panel_usuario_reactivar"),
]
