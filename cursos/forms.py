# ============================================================
# CURSOS/FORMS.PY / FORMULARIOS DEL PANEL PARA ÁREAS Y CURSOS
# ModelForm con validación del modelo (clean + constraints), de modo
# que el panel HTML aplica las mismas reglas que la API.
# ============================================================
from django import forms

from core.forms import FormularioBootstrapMixin

from .models import AreaConocimiento, Curso


class AreaForm(FormularioBootstrapMixin, forms.ModelForm):
    """Crear o editar un área de conocimiento."""

    class Meta:
        model = AreaConocimiento
        fields = ["nombre", "descripcion", "icono"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "icono": forms.TextInput(attrs={"placeholder": "bi-code-slash"}),
        }

    def clean_icono(self):
        icono = (self.cleaned_data.get("icono") or "").strip()
        if icono and not icono.startswith("bi-"):
            raise forms.ValidationError("El ícono debe ser una clase de Bootstrap Icons que comience con «bi-».")
        return icono


class CursoForm(FormularioBootstrapMixin, forms.ModelForm):
    """Crear o editar un curso; los cupos disponibles se ajustan solos."""

    class Meta:
        model = Curso
        fields = [
            "titulo", "descripcion", "area", "tipo", "modalidad", "costo_matricula",
            "fecha_inicio", "fecha_termino", "cupos_maximos",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_termino": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "costo_matricula": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "cupos_maximos": forms.NumberInput(attrs={"min": 1}),
        }
        help_texts = {
            "cupos_maximos": "Si lo cambias, los cupos disponibles se ajustan según la diferencia.",
            "costo_matricula": "En pesos chilenos, sin puntos.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        areas = AreaConocimiento.objects.filter(activo=True)
        if self.instance.pk:
            areas = AreaConocimiento.objects.filter(pk=self.instance.area_id) | areas
        self.fields["area"].queryset = areas.distinct()
        self.fields["area"].empty_label = "Selecciona un área"
