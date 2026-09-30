#!/usr/bin/env python
# ============================================================
# MANAGE.PY / UTILIDAD DE LÍNEA DE COMANDOS DE DJANGO
# migrate, runserver, test, seed_data, simular_concurrencia, etc.
# Si la consola no soporta algún carácter (✓), se reemplaza en vez
# de detener el comando.
# ============================================================
import os
import sys


def main():
    """Ejecuta los comandos de administración del proyecto."""
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academia_bootcamps.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Activaste el entorno virtual (venv) e instalaste requirements.txt?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
