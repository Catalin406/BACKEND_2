# ============================================================
# MATRICULAS/FILTROS.PY / FILTROS DE MATRÍCULAS E INSCRIPCIONES
# MatriculaFilter: estado, estudiante, curso (a través del detalle)
# y rango de fechas de creación. InscripcionFilter: curso y activa.
# Se usan en la API del coordinador y en el panel HTML.
# ============================================================
import django_filters
from django import forms

from cursos.models import Curso
from usuarios.models import Rol, Usuario

from .models import EstadoMatricula, Inscripcion, Matricula


class MatriculaFilter(django_filters.FilterSet):
    """Filtros de matrículas para el coordinador."""

    estado = django_filters.ChoiceFilter(
        choices=EstadoMatricula.choices, label="Estado", empty_label="Todos los estados"
    )
    estudiante = django_filters.ModelChoiceFilter(
        queryset=Usuario.objects.filter(rol=Rol.ESTUDIANTE), label="Estudiante", empty_label="Todos los estudiantes"
    )
    curso = django_filters.ModelChoiceFilter(
        field_name="detalles__curso", queryset=Curso.objects.all(), label="Curso",
        empty_label="Todos los cursos", distinct=True,
    )
    fecha_desde = django_filters.DateFilter(field_name="creada_en", lookup_expr="date__gte", label="Creada desde")
    fecha_hasta = django_filters.DateFilter(field_name="creada_en", lookup_expr="date__lte", label="Creada hasta")

    class Meta:
        model = Matricula
        fields = ["estado", "estudiante", "curso", "fecha_desde", "fecha_hasta"]


class InscripcionFilter(django_filters.FilterSet):
    """Filtros de inscripciones oficiales (inscritos por curso)."""

    curso = django_filters.ModelChoiceFilter(
        field_name="detalle__curso", queryset=Curso.objects.all(), label="Curso", empty_label="Todos los cursos"
    )
    activa = django_filters.BooleanFilter(
        label="Estado",
        widget=forms.Select(choices=[("", "Todas"), ("true", "Activas"), ("false", "Inactivas")]),
    )

    class Meta:
        model = Inscripcion
        fields = ["curso", "activa"]
