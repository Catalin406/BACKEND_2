# ============================================================
# USUARIOS/FORMS.PY / FORMULARIO DE USUARIOS DEL PANEL
# Permite elegir el rol y define la contraseña con set_password
# (nunca se guarda en texto plano). Al crear, la contraseña es
# obligatoria; al editar, es opcional.
# ============================================================
from django import forms
from django.contrib.auth.password_validation import validate_password

from core.forms import FormularioBootstrapMixin

from .models import Usuario


class UsuarioForm(FormularioBootstrapMixin, forms.ModelForm):
    """Crear o editar un usuario con su rol."""

    password1 = forms.CharField(
        label="Contraseña", required=False, strip=False, widget=forms.PasswordInput(render_value=False)
    )
    password2 = forms.CharField(
        label="Confirmar contraseña", required=False, strip=False, widget=forms.PasswordInput(render_value=False)
    )

    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "rut", "telefono", "rol"]
        labels = {"username": "Nombre de usuario", "first_name": "Nombre", "last_name": "Apellido"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        if self.instance.pk:
            self.fields["password1"].help_text = "Déjala vacía para mantener la contraseña actual."
        else:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(p1, self.instance)
                except forms.ValidationError as error:
                    self.add_error("password1", error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario
