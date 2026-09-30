# ============================================================
# MATRICULAS/FORMS.PY / FORMULARIO DE CAMBIO DE ESTADO DEL PANEL
# Solo acepta los estados a los que la matrícula puede pasar según
# TRANSICIONES_PERMITIDAS (la validación final la hace el servicio).
# ============================================================
from django import forms

from core.forms import FormularioBootstrapMixin

from .models import EstadoMatricula


class CambioEstadoForm(FormularioBootstrapMixin, forms.Form):
    """Nuevo estado y observación para el historial."""

    estado = forms.ChoiceField(choices=EstadoMatricula.choices, widget=forms.HiddenInput)
    observacion = forms.CharField(
        label="Observación", required=False, max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Motivo del cambio (opcional)"}),
    )
