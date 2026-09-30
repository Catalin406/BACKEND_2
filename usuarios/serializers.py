# ============================================================
# USUARIOS/SERIALIZERS.PY / REGISTRO, PERFIL, LOGOUT Y CRUD DE USUARIOS
# Las contraseñas siempre pasan por validate_password y se guardan
# con set_password (hash). El registro público solo crea ESTUDIANTES:
# el rol no se puede elegir desde afuera.
# ============================================================
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Rol, Usuario


def _validar_contrasena(password, usuario=None):
    """Aplica los validadores de contraseña de Django con mensajes en español."""
    try:
        validate_password(password, usuario)
    except DjangoValidationError as error:
        raise serializers.ValidationError(list(error.messages))
    return password


def _validar_rut_unico(rut, instancia=None):
    """Verifica que el RUT (si viene) no pertenezca a otro usuario."""
    if not rut:
        return None
    existentes = Usuario.objects.filter(rut=rut)
    if instancia is not None:
        existentes = existentes.exclude(pk=instancia.pk)
    if existentes.exists():
        raise serializers.ValidationError("Ya existe un usuario con este RUT.")
    return rut


# ============================================================
# REGISTRO PÚBLICO (SIEMPRE ESTUDIANTE)
# ============================================================
class RegistroSerializer(serializers.ModelSerializer):
    """Crea una cuenta de estudiante."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirmacion = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "email", "first_name", "last_name", "rut", "telefono",
            "password", "password_confirmacion", "rol",
        ]
        read_only_fields = ["id", "rol"]
        extra_kwargs = {"email": {"required": True}}

    def validate_rut(self, valor):
        return _validar_rut_unico(valor)

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirmacion"):
            raise serializers.ValidationError({"password_confirmacion": "Las contraseñas no coinciden."})
        usuario_temporal = Usuario(username=attrs.get("username"), email=attrs.get("email"))
        _validar_contrasena(attrs["password"], usuario_temporal)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        usuario = Usuario(**validated_data, rol=Rol.ESTUDIANTE)
        usuario.set_password(password)
        usuario.save()
        return usuario


# ============================================================
# LOGOUT: BLACKLIST DEL REFRESH TOKEN
# ============================================================
class LogoutSerializer(serializers.Serializer):
    """Recibe el refresh token y lo invalida."""

    refresh = serializers.CharField()

    def validate_refresh(self, valor):
        try:
            self._token = RefreshToken(valor)
        except TokenError:
            raise serializers.ValidationError("El refresh token no es válido o ya fue invalidado.")
        return valor

    def save(self, **kwargs):
        self._token.blacklist()


# ============================================================
# PERFIL Y CRUD DE USUARIOS (COORDINADOR)
# ============================================================
class UsuarioSerializer(serializers.ModelSerializer):
    """Usuario completo para el coordinador (la contraseña es solo de escritura)."""

    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={"input_type": "password"}
    )

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "email", "first_name", "last_name", "rut", "telefono",
            "rol", "rol_display", "is_active", "date_joined", "last_login", "password",
        ]
        read_only_fields = ["id", "is_active", "date_joined", "last_login"]

    def validate_rut(self, valor):
        return _validar_rut_unico(valor, self.instance)

    def validate(self, attrs):
        password = attrs.get("password")
        if self.instance is None and not password:
            raise serializers.ValidationError({"password": "La contraseña es obligatoria al crear un usuario."})
        if password:
            candidato = self.instance or Usuario(username=attrs.get("username"), email=attrs.get("email"))
            try:
                _validar_contrasena(password, candidato)
            except serializers.ValidationError as error:
                raise serializers.ValidationError({"password": error.detail})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class PerfilSerializer(serializers.ModelSerializer):
    """Datos del usuario autenticado."""

    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "email", "first_name", "last_name", "nombre_completo",
            "rut", "telefono", "rol", "rol_display", "last_login",
        ]
        read_only_fields = fields


class UsuarioResumenSerializer(serializers.ModelSerializer):
    """Representación breve del usuario para anidar en otros recursos."""

    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "username", "nombre_completo", "email"]
        read_only_fields = fields
