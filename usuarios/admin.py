# ============================================================
# USUARIOS/ADMIN.PY / REGISTRO DEL USUARIO EN DJANGO ADMIN
# Apoyo al criterio "Django Admin": listado, filtros y búsqueda.
# ============================================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin del usuario con rol, RUT y teléfono."""

    list_display = ["username", "email", "first_name", "last_name", "rol", "is_active", "is_staff"]
    list_filter = ["rol", "is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name", "rut"]
    fieldsets = UserAdmin.fieldsets + (("Datos de la academia", {"fields": ("rol", "rut", "telefono")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Datos de la academia", {"fields": ("email", "rol")}),)
