# ============================================================
# CURSOS/FILTROS.PY / FILTROS DE LA OFERTA ACADÉMICA (django-filter)
# CursoFilter se usa en GET /api/cursos/ y también en la vista HTML
# de la oferta (/cursos/), así la API y la web filtran igual.
# ============================================================
import django_filters
from django import forms

from .models import AreaConocimiento, Curso, Modalidad, TipoCurso


class CursoFilter(django_filters.FilterSet):
    """Filtros por área, tipo, modalidad, costo, fecha de inicio y cupos."""

    area = django_filters.ModelChoiceFilter(
        queryset=AreaConocimiento.objects.filter(activo=True),
        label="Área",
        empty_label="Todas las áreas",
    )
    area_nombre = django_filters.CharFilter(
        field_name="area__nombre", lookup_expr="icontains", label="Nombre del área contiene"
    )
    tipo = django_filters.ChoiceFilter(choices=TipoCurso.choices, label="Tipo", empty_label="Todos los tipos")
    modalidad = django_filters.ChoiceFilter(
        choices=Modalidad.choices, label="Modalidad", empty_label="Todas las modalidades"
    )
    costo_min = django_filters.NumberFilter(
        field_name="costo_matricula", lookup_expr="gte", label="Costo mínimo (CLP)"
    )
    costo_max = django_filters.NumberFilter(
        field_name="costo_matricula", lookup_expr="lte", label="Costo máximo (CLP)"
    )
    inicio_desde = django_filters.DateFilter(
        field_name="fecha_inicio", lookup_expr="gte", label="Inicio desde"
    )
    inicio_hasta = django_filters.DateFilter(
        field_name="fecha_inicio", lookup_expr="lte", label="Inicio hasta"
    )
    con_cupos = django_filters.BooleanFilter(
        method="filtrar_con_cupos",
        label="Disponibilidad",
        widget=forms.Select(choices=[("", "Todos"), ("true", "Con cupos disponibles"), ("false", "Agotados")]),
    )

    class Meta:
        model = Curso
        fields = [
            "area", "area_nombre", "tipo", "modalidad", "costo_min", "costo_max",
            "inicio_desde", "inicio_hasta", "con_cupos",
        ]

    def filtrar_con_cupos(self, queryset, name, value):
        """true: cupos_disponibles > 0; false: cursos agotados."""
        if value is None:
            return queryset
        if value:
            return queryset.filter(cupos_disponibles__gt=0)
        return queryset.filter(cupos_disponibles=0)
