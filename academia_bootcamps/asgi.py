# ============================================================
# ACADEMIA_BOOTCAMPS/ASGI.PY / PUNTO DE ENTRADA ASGI
# Expone "application" para servidores ASGI (uvicorn, daphne).
# ============================================================
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academia_bootcamps.settings")

application = get_asgi_application()
