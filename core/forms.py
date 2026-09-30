# ============================================================
# CORE/FORMS.PY / ESTILO BOOTSTRAP COMÚN PARA LOS FORMULARIOS
# Mezcla que agrega las clases de Bootstrap a cada widget, para que
# todos los ModelForm del panel se vean iguales y marquen en rojo los
# campos con errores.
# ============================================================
from django import forms


class FormularioBootstrapMixin:
    """Agrega form-control / form-select / form-check-input a los widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, campo in self.fields.items():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                clase = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                clase = "form-select"
            else:
                clase = "form-control"
            if self.is_bound and nombre in self.errors:
                clase += " is-invalid"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {clase}".strip()


def estilizar_filtro(formulario):
    """Aplica el mismo estilo a los formularios generados por django-filter."""
    for campo in formulario.fields.values():
        widget = campo.widget
        if isinstance(widget, (forms.Select, forms.NullBooleanSelect)):
            widget.attrs["class"] = "form-select form-select-sm"
        else:
            widget.attrs["class"] = "form-control form-control-sm"
        if isinstance(widget, forms.DateInput):
            widget.input_type = "date"
            widget.format = "%Y-%m-%d"
    return formulario
