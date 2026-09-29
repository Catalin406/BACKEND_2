# ============================================================
# USUARIOS/MODELS.PY / MODELO DE USUARIO PERSONALIZADO
# Extiende AbstractUser para agregar el rol (Estudiante o
# Coordinador Académico), un email único, RUT y teléfono.
# El rol es la base de la matriz de permisos de la API JWT.
# ============================================================
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


# ============================================================
# CHOICES DE ROL
# Valores en mayúsculas porque viajan en el claim "rol" del JWT.
# ============================================================
class Rol(models.TextChoices):
    """Roles de negocio de la plataforma."""

    ESTUDIANTE = "ESTUDIANTE", "Estudiante"
    COORDINADOR = "COORDINADOR", "Coordinador Académico"


# ============================================================
# MODELO USUARIO
# is_staff se sincroniza con el rol en save() para que
# IsAdminUser de DRF y el admin de Django reconozcan al coordinador.
# Borrado lógico: "eliminar" = is_active=False.
# ============================================================
class Usuario(AbstractUser):
    """Usuario de la academia con rol de negocio."""

    Rol = Rol

    rol = models.CharField(
        "rol", max_length=20, choices=Rol.choices, default=Rol.ESTUDIANTE, db_index=True
    )
    email = models.EmailField(
        "correo electrónico",
        unique=True,
        error_messages={"unique": "Ya existe un usuario con este correo electrónico."},
    )
    rut = models.CharField(
        "RUT", max_length=12, blank=True, null=True, help_text="Opcional. Ej.: 12.345.678-9"
    )
    telefono = models.CharField("teléfono", max_length=20, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]
        constraints = [
            # RUT opcional, pero único cuando se informa.
            models.UniqueConstraint(
                fields=["rut"],
                condition=Q(rut__isnull=False) & ~Q(rut=""),
                name="usuario_rut_unico_si_existe",
                violation_error_message="Ya existe un usuario con este RUT.",
            ),
        ]

    def __str__(self):
        nombre = self.get_full_name() or self.username
        return f"{nombre} ({self.get_rol_display()})"

    # ============================================================
    # SINCRONIZACIÓN DE ROL Y PERMISOS DE STAFF
    # Un superusuario siempre es coordinador; el coordinador es staff.
    # ============================================================
    def save(self, *args, **kwargs):
        """Normaliza el RUT vacío y sincroniza is_staff con el rol."""
        if not self.rut:
            self.rut = None
        if self.is_superuser:
            self.rol = Rol.COORDINADOR
        self.is_staff = self.rol == Rol.COORDINADOR
        super().save(*args, **kwargs)

    @property
    def es_coordinador(self):
        """True si el usuario es Coordinador Académico."""
        return self.rol == Rol.COORDINADOR

    @property
    def es_estudiante(self):
        """True si el usuario es Estudiante."""
        return self.rol == Rol.ESTUDIANTE

    @property
    def nombre_completo(self):
        """Nombre y apellido, o el username si no los tiene."""
        return self.get_full_name() or self.username
