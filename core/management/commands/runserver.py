# ============================================================
# CORE/MANAGEMENT/COMMANDS/RUNSERVER.PY / RUNSERVER SIN 404 EN /static/
# El runserver de django.contrib.staticfiles atiende /static/ con un
# StaticFilesHandler ANTES de las URLs y del middleware del proyecto,
# así que un archivo inexistente mostraba el 404 de Django. Este
# comando lo reemplaza (core va antes de django.contrib.staticfiles
# en INSTALLED_APPS, por eso Django encuentra primero este runserver)
# y usa un manejador propio que, ante un Http404, responde con la
# misma pantalla de redirección del resto del sitio.
# ============================================================
from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.management.commands.runserver import Command as RunserverStaticfiles
from django.core.management.commands.runserver import Command as RunserverBase
from django.http import Http404


# ============================================================
# MANEJADOR DE ESTÁTICOS CON REDIRECCIÓN
# Los archivos reales se sirven igual que antes; solo cambia la
# respuesta cuando el archivo no existe (o se pide /static/ a secas,
# que Django rechaza con Http404 por no listar directorios).
# ============================================================
class ManejadorEstaticosConRedireccion(StaticFilesHandler):
    """StaticFilesHandler que convierte los 404 en la pantalla de redirección."""

    def get_response(self, request):
        """Sirve el archivo estático o, si no existe, renderiza core/redireccion.html."""
        try:
            return self.serve(request)
        except Http404:
            from core.views import renderizar_redireccion

            return renderizar_redireccion(request)


# ============================================================
# COMANDO RUNSERVER
# Hereda del runserver de staticfiles para conservar sus opciones
# (--nostatic, --insecure) y solo cambia el manejador que envuelve
# a la aplicación WSGI.
# ============================================================
class Command(RunserverStaticfiles):
    """runserver que sirve estáticos sin mostrar nunca el 404 de Django."""

    def get_handler(self, *args, **options):
        """Envuelve el manejador WSGI base con ManejadorEstaticosConRedireccion."""
        handler = RunserverBase.get_handler(self, *args, **options)
        if options["use_static_handler"] and (settings.DEBUG or options["insecure_serving"]):
            return ManejadorEstaticosConRedireccion(handler)
        return handler
