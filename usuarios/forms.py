# ============================================================
# USUARIOS/FORMS.PY / FORMULARIO DE USUARIOS DEL PANEL
# Permite elegir el rol y define la contraseña con set_password
# (nunca se guarda en texto plano). Al crear, la contraseña es
# obligatoria; al editar, es opcional.
# ============================================================
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from core.forms import FormularioBootstrapMixin

from .models import Rol, Usuario


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


# ============================================================
# LOGIN DEL PANEL
# Solo el Coordinador Académico puede iniciar sesión en el panel.
# confirm_login_allowed corre después de validar la contraseña, así
# que el mensaje no revela si una cuenta existe a quien no la conoce.
# ============================================================
class LoginPanelForm(FormularioBootstrapMixin, AuthenticationForm):
    """AuthenticationForm que rechaza a quien no sea coordinador."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not (user.is_staff and user.rol == Rol.COORDINADOR):
            raise forms.ValidationError(
                "Solo el Coordinador Académico puede iniciar sesión en el panel de gestión.",
                code="no_coordinador",
            )
