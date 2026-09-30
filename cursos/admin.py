# ============================================================
# CURSOS/ADMIN.PY / REGISTRO DE ÁREAS Y CURSOS EN DJANGO ADMIN
# cupos_disponibles es de solo lectura: lo gestionan los servicios.
# ============================================================
from django.contrib import admin

from .models import AreaConocimiento, Curso


@admin.register(AreaConocimiento)
class AreaConocimientoAdmin(admin.ModelAdmin):
    """Admin de áreas de conocimiento."""

    list_display = ["nombre", "icono", "activo", "creado_en"]
    list_filter = ["activo"]
    search_fields = ["nombre", "descripcion"]


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    """Admin de cursos con sus cupos."""

    list_display = [
        "titulo", "area", "tipo", "modalidad", "costo_matricula", "fecha_inicio",
        "cupos_maximos", "cupos_disponibles", "activo",
    ]
    list_filter = ["area", "tipo", "modalidad", "activo"]
    search_fields = ["titulo", "descripcion", "area__nombre"]
    readonly_fields = ["cupos_disponibles", "creado_en", "actualizado_en"]
    date_hierarchy = "fecha_inicio"
