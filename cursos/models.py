# ============================================================
# CURSOS/MODELS.PY / OFERTA ACADÉMICA
# AreaConocimiento y Curso (cursos, bootcamps y talleres).
# Reglas de integridad en la BD: costo > 0, fechas coherentes,
# 0 <= cupos_disponibles <= cupos_maximos y una cohorte por fecha.
# 3FN: el curso guarda solo la FK al área, nunca su nombre.
# ============================================================
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q


# ============================================================
# CHOICES DEL CURSO
# ============================================================
class TipoCurso(models.TextChoices):
    """Tipo de programa académico."""

    CURSO = "CURSO", "Curso"
    BOOTCAMP = "BOOTCAMP", "Bootcamp"
    TALLER = "TALLER", "Taller"


class Modalidad(models.TextChoices):
    """Modalidad de dictación."""

    PRESENCIAL = "PRESENCIAL", "Presencial"
    ONLINE = "ONLINE", "Online"
    HIBRIDA = "HIBRIDA", "Híbrida"


# ============================================================
# ÁREA DE CONOCIMIENTO
# Agrupa los cursos. Baja lógica con "activo".
# ============================================================
class AreaConocimiento(models.Model):
    """Área temática de la academia (Desarrollo Web, Ciencia de Datos, etc.)."""

    nombre = models.CharField(
        "nombre",
        max_length=100,
        unique=True,
        error_messages={"unique": "Ya existe un área con este nombre."},
    )
    descripcion = models.TextField("descripción", blank=True)
    icono = models.CharField(
        "ícono",
        max_length=50,
        blank=True,
        help_text="Clase de Bootstrap Icons, por ejemplo: bi-code-slash",
    )
    activo = models.BooleanField("activo", default=True, db_index=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "área de conocimiento"
        verbose_name_plural = "áreas de conocimiento"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def icono_css(self):
        """Clase de ícono a mostrar (con un ícono por defecto)."""
        return self.icono or "bi-mortarboard"


# ============================================================
# CURSO / BOOTCAMP / TALLER
# cupos_disponibles no es editable desde formularios: lo gestionan
# save() (al crear o cambiar el máximo) y los servicios de matrícula
# con expresiones F() bajo bloqueo de fila.
# ============================================================
class Curso(models.Model):
    """Cohorte de un curso, bootcamp o taller con cupos limitados."""

    titulo = models.CharField("título", max_length=150)
    descripcion = models.TextField("descripción")
    area = models.ForeignKey(
        AreaConocimiento,
        verbose_name="área",
        on_delete=models.PROTECT,
        related_name="cursos",
    )
    tipo = models.CharField("tipo", max_length=10, choices=TipoCurso.choices, default=TipoCurso.CURSO)
    modalidad = models.CharField(
        "modalidad", max_length=10, choices=Modalidad.choices, default=Modalidad.ONLINE
    )
    costo_matricula = models.DecimalField(
        "costo de matrícula (CLP)", max_digits=12, decimal_places=0
    )
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_termino = models.DateField("fecha de término")
    cupos_maximos = models.PositiveIntegerField("cupos máximos")
    cupos_disponibles = models.PositiveIntegerField("cupos disponibles", default=0, editable=False)
    activo = models.BooleanField("activo", default=True, db_index=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "curso"
        verbose_name_plural = "cursos"
        ordering = ["fecha_inicio", "titulo"]
        constraints = [
            models.UniqueConstraint(
                fields=["titulo", "fecha_inicio"],
                name="curso_cohorte_unica",
                violation_error_message="Ya existe una cohorte de este curso con la misma fecha de inicio.",
            ),
            models.CheckConstraint(
                condition=Q(costo_matricula__gt=0),
                name="curso_costo_positivo",
                violation_error_message="El costo de matrícula debe ser mayor a 0.",
            ),
            models.CheckConstraint(
                condition=Q(fecha_termino__gte=F("fecha_inicio")),
                name="curso_fechas_coherentes",
                violation_error_message="La fecha de término no puede ser anterior a la fecha de inicio.",
            ),
            models.CheckConstraint(
                condition=Q(cupos_maximos__gte=1),
                name="curso_cupos_maximos_minimo_1",
                violation_error_message="El curso debe tener al menos 1 cupo.",
            ),
            models.CheckConstraint(
                condition=Q(cupos_disponibles__gte=0) & Q(cupos_disponibles__lte=F("cupos_maximos")),
                name="curso_cupos_disponibles_validos",
                violation_error_message="Los cupos disponibles deben estar entre 0 y el máximo de cupos.",
            ),
        ]
        indexes = [
            models.Index(fields=["area"], name="curso_area_idx"),
            models.Index(fields=["fecha_inicio"], name="curso_fecha_inicio_idx"),
            models.Index(fields=["costo_matricula"], name="curso_costo_idx"),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.fecha_inicio:%d-%m-%Y})"

    # ============================================================
    # PROPIEDADES CALCULADAS (no se guardan: 3FN)
    # ============================================================
    @property
    def duracion_dias(self):
        """Días de duración, contando inicio y término."""
        if self.fecha_inicio and self.fecha_termino:
            return (self.fecha_termino - self.fecha_inicio).days + 1
        return None

    @property
    def cupos_ocupados(self):
        """Cupos tomados por inscripciones activas."""
        return self.cupos_maximos - self.cupos_disponibles

    @property
    def porcentaje_ocupacion(self):
        """Porcentaje de ocupación (0 a 100) para la barra de cupos."""
        if not self.cupos_maximos:
            return 0
        return round(self.cupos_ocupados * 100 / self.cupos_maximos)

    @property
    def tiene_cupos(self):
        """True si queda al menos un cupo libre."""
        return self.cupos_disponibles > 0

    # ============================================================
    # VALIDACIÓN DE NEGOCIO
    # El máximo no puede quedar bajo los cupos ya ocupados.
    # ============================================================
    def clean(self):
        """Valida fechas y que el nuevo máximo no sea menor a los cupos ocupados."""
        errores = {}
        if self.fecha_inicio and self.fecha_termino and self.fecha_termino < self.fecha_inicio:
            errores["fecha_termino"] = "La fecha de término no puede ser anterior a la fecha de inicio."
        if self.costo_matricula is not None and self.costo_matricula <= 0:
            errores["costo_matricula"] = "El costo de matrícula debe ser mayor a 0."
        if self.cupos_maximos is not None:
            if self.cupos_maximos < 1:
                errores["cupos_maximos"] = "El curso debe tener al menos 1 cupo."
            elif self.pk:
                ocupados = self.cupos_ocupados_en_bd()
                if self.cupos_maximos < ocupados:
                    errores["cupos_maximos"] = (
                        f"No puedes dejar {self.cupos_maximos} cupos máximos: "
                        f"ya hay {ocupados} cupos ocupados por inscripciones activas."
                    )
        if errores:
            raise ValidationError(errores)

    def cupos_ocupados_en_bd(self):
        """Cupos ocupados según los valores actualmente guardados en la BD."""
        actual = Curso.objects.filter(pk=self.pk).values("cupos_maximos", "cupos_disponibles").first()
        if not actual:
            return 0
        return actual["cupos_maximos"] - actual["cupos_disponibles"]

    # ============================================================
    # AJUSTE AUTOMÁTICO DE CUPOS AL GUARDAR
    # Al crear: disponibles = máximo. Al editar: disponibles se ajusta
    # según la diferencia del máximo, leyendo la fila con bloqueo para
    # no pisar un descuento concurrente hecho por una confirmación.
    # ============================================================
    def save(self, *args, **kwargs):
        """Guarda el curso manteniendo coherentes los cupos disponibles."""
        with transaction.atomic():
            if self.pk and not self._state.adding:
                actual = (
                    Curso.objects.select_for_update()
                    .only("cupos_maximos", "cupos_disponibles")
                    .get(pk=self.pk)
                )
                ocupados = actual.cupos_maximos - actual.cupos_disponibles
                if self.cupos_maximos < ocupados:
                    raise ValidationError(
                        {
                            "cupos_maximos": (
                                f"No puedes dejar {self.cupos_maximos} cupos máximos: "
                                f"ya hay {ocupados} cupos ocupados por inscripciones activas."
                            )
                        }
                    )
                self.cupos_disponibles = self.cupos_maximos - ocupados
            else:
                self.cupos_disponibles = self.cupos_maximos
            super().save(*args, **kwargs)
