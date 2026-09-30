# ============================================================
# USUARIOS/TOKENS.PY / JWT CON CLAIMS DE ROL
# TokenConRolSerializer hereda de TokenObtainPairSerializer y agrega
# al payload del token los claims rol, username, email y
# nombre_completo. Los permisos de la API leen el claim "rol"
# directamente desde request.auth.
# ============================================================
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class TokenConRolSerializer(TokenObtainPairSerializer):
    """Emite access/refresh con el rol del usuario como claim."""

    default_error_messages = {
        "no_active_account": "Usuario o contraseña incorrectos, o la cuenta está desactivada."
    }

    # ============================================================
    # CLAIMS PERSONALIZADOS
    # Se agregan al refresh y se heredan en el access token.
    # ============================================================
    @classmethod
    def get_token(cls, user):
        """Agrega rol, username, email y nombre_completo al token."""
        token = super().get_token(user)
        token["rol"] = user.rol
        token["username"] = user.username
        token["email"] = user.email
        token["nombre_completo"] = user.get_full_name() or user.username
        return token

    # ============================================================
    # RESPUESTA DEL LOGIN
    # Además de access y refresh devuelve el rol y los datos básicos.
    # ============================================================
    def validate(self, attrs):
        """Devuelve access, refresh, rol y usuario."""
        data = super().validate(attrs)
        data["rol"] = self.user.rol
        data["usuario"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "nombre_completo": self.user.get_full_name() or self.user.username,
            "rol": self.user.rol,
            "rol_display": self.user.get_rol_display(),
        }
        return data
