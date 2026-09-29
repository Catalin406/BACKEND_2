# ============================================================
# CORE/MIDDLEWARE.PY / TERCERA CAPA CONTRA RUTAS INEXISTENTES
# Si cualquier vista HTML lanza Http404 o devuelve un 404 (incluso
# con DEBUG=True, cuando handler404 no actúa), se reemplaza la
# respuesta por la pantalla de redirección al inicio.
# Las rutas de la API conservan su respuesta JSON controlada.
# ============================================================
from django.http import Http404


class RedireccionNoEncontradaMiddleware:
    """Convierte los 404 de las páginas HTML en la pantalla de redirección."""

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _es_api(request):
        """True si la petición apunta a la API REST (respuestas JSON)."""
        return request.path.startswith("/api/")

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404 and not self._es_api(request):
            from core.views import renderizar_redireccion

            return renderizar_redireccion(request)
        return response

    def process_exception(self, request, exception):
        """Captura Http404 lanzado por una vista HTML."""
        if isinstance(exception, Http404) and not self._es_api(request):
            from core.views import renderizar_redireccion

            return renderizar_redireccion(request)
        return None
