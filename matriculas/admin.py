# ============================================================
# MATRICULAS/ADMIN.PY / REGISTRO DE MATRÍCULAS EN DJANGO ADMIN
# El estado se cambia desde la API o el panel (servicios), no aquí,
# para no saltarse la liberación de cupos: por eso es de solo lectura.
# ============================================================
from django.contrib import admin

from .models import DetalleMatricula, HistorialEstadoMatricula, Inscripcion, Matricula


class DetalleInline(admin.TabularInline):
    """Detalles de la matrícula."""

    model = DetalleMatricula
    extra = 0
    can_delete = False
    readonly_fields = ["curso", "costo_matricula"]


class HistorialInline(admin.TabularInline):
    """Historial de estados."""

    model = HistorialEstadoMatricula
    extra = 0
    can_delete = False
    readonly_fields = ["estado_anterior", "estado_nuevo", "cambiado_por", "fecha", "observacion"]


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    """Admin de matrículas."""

    list_display = ["codigo", "estudiante", "estado", "total", "creada_en", "pagada_en"]
    list_filter = ["estado", "creada_en"]
    search_fields = ["codigo", "estudiante__username", "estudiante__email"]
    readonly_fields = ["codigo", "estudiante", "estado", "creada_en", "pagada_en", "actualizada_en"]
    inlines = [DetalleInline, HistorialInline]


@admin.register(DetalleMatricula)
class DetalleMatriculaAdmin(admin.ModelAdmin):
    """Admin de detalles con costo congelado."""

    list_display = ["matricula", "curso", "costo_matricula"]
    list_filter = ["curso__area"]
    search_fields = ["matricula__codigo", "curso__titulo"]


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    """Admin de inscripciones oficiales."""

    list_display = ["codigo", "detalle", "activa", "emitida_en"]
    list_filter = ["activa", "detalle__curso"]
    search_fields = ["codigo", "detalle__curso__titulo", "detalle__matricula__estudiante__username"]


@admin.register(HistorialEstadoMatricula)
class HistorialEstadoMatriculaAdmin(admin.ModelAdmin):
    """Admin del historial de estados."""

    list_display = ["matricula", "estado_anterior", "estado_nuevo", "cambiado_por", "fecha"]
    list_filter = ["estado_nuevo", "fecha"]
    search_fields = ["matricula__codigo", "observacion"]
