# ============================================================
# ACADEMIA_BOOTCAMPS/WSGI.PY / PUNTO DE ENTRADA WSGI
# Expone "application" para servidores WSGI (gunicorn, mod_wsgi).
# ============================================================
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academia_bootcamps.settings")

application = get_wsgi_application()
