# ============================================================
# CARRO/ADMIN.PY / REGISTRO DE CARROS E ÍTEMS EN DJANGO ADMIN
# ============================================================
from django.contrib import admin

from .models import CarroMatricula, ItemCarroMatricula


class ItemCarroInline(admin.TabularInline):
    """Ítems del carro dentro de su ficha."""

    model = ItemCarroMatricula
    extra = 0
    fields = ["curso", "activo", "agregado_en"]
    readonly_fields = ["agregado_en"]


@admin.register(CarroMatricula)
class CarroMatriculaAdmin(admin.ModelAdmin):
    """Admin del carro persistente."""

    list_display = ["estudiante", "cantidad_cursos", "total", "actualizado_en"]
    list_filter = ["actualizado_en"]
    search_fields = ["estudiante__username", "estudiante__email"]
    inlines = [ItemCarroInline]


@admin.register(ItemCarroMatricula)
class ItemCarroMatriculaAdmin(admin.ModelAdmin):
    """Admin de ítems del carro."""

    list_display = ["carro", "curso", "activo", "agregado_en"]
    list_filter = ["activo", "curso__area"]
    search_fields = ["carro__estudiante__username", "curso__titulo"]
