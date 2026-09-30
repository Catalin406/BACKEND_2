# ============================================================
# CARRO/FORMS.PY / FORMULARIOS DEL PANEL DE CARROS
# Selector de estudiante y formulario para agregar un curso. Las
# reglas (duplicado, inactivo, sin cupos) las aplica carro/servicios.py
# para que el mensaje sea el mismo que entrega la API.
# ============================================================
from django import forms

from core.forms import FormularioBootstrapMixin
from cursos.models import Curso
from usuarios.models import Rol, Usuario


class SeleccionEstudianteForm(FormularioBootstrapMixin, forms.Form):
    """"Ver carro de: [estudiante]"."""

    estudiante = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol=Rol.ESTUDIANTE, is_active=True).order_by("username"),
        label="Ver carro de",
        empty_label="Selecciona un estudiante",
    )


class AgregarCursoCarroForm(FormularioBootstrapMixin, forms.Form):
    """Curso a agregar al carro del estudiante seleccionado."""

    curso = forms.ModelChoiceField(
        queryset=Curso.objects.filter(activo=True, area__activo=True).select_related("area").order_by("titulo"),
        label="Curso a agregar",
        empty_label="Selecciona un curso",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso"].label_from_instance = (
            lambda c: f"{c.titulo} · {c.fecha_inicio:%d-%m-%Y} · {c.cupos_disponibles} cupos"
        )
