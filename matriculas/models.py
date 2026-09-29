# ============================================================
# MATRICULAS/MODELS.PY / MATRÍCULAS, DETALLES, INSCRIPCIONES E HISTORIAL
# Matricula es la orden del estudiante (código UUID y estado),
# DetalleMatricula congela el costo de cada curso al confirmar,
# Inscripcion es el comprobante oficial (UUID) por curso y
# HistorialEstadoMatricula audita cada transición de estado.
# El total no se guarda: se calcula con Sum (3FN).
# ============================================================
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Sum


# ============================================================
# CHOICES DE ESTADO DE LA MATRÍCULA
# ============================================================
class EstadoMatricula(models.TextChoices):
    """Ciclo de vida de una matrícula."""

    PENDIENTE = "PENDIENTE", "Pendiente"
    PAGADO = "PAGADO", "Pagado"
    COMPLETADO = "COMPLETADO", "Completado"
    CANCELADO = "CANCELADO", "Cancelado"


# ============================================================
# MANAGER CON TOTAL ANOTADO
# Permite listar matrículas con su total sin consultas extra.
# ============================================================
class MatriculaQuerySet(models.QuerySet):
    """QuerySet con utilidades para matrículas."""

    def con_total(self):
        """Anota total_anotado = suma de los costos congelados."""
        return self.annotate(total_anotado=Sum("detalles__costo_matricula"))


# ============================================================
# MATRÍCULA (ORDEN)
# ============================================================
class Matricula(models.Model):
    """Orden de matrícula de un estudiante."""

    codigo = models.UUIDField("código", unique=True, default=uuid.uuid4, editable=False)
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="matriculas",
    )
    estado = models.CharField(
        "estado",
        max_length=12,
        choices=EstadoMatricula.choices,
        default=EstadoMatricula.PENDIENTE,
        db_index=True,
    )
    creada_en = models.DateTimeField("creada en", auto_now_add=True)
    pagada_en = models.DateTimeField("pagada en", null=True, blank=True)
    actualizada_en = models.DateTimeField("actualizada en", auto_now=True)

    objects = MatriculaQuerySet.as_manager()

    class Meta:
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"
        ordering = ["-creada_en"]
        indexes = [models.Index(fields=["estudiante", "estado"], name="matricula_estud_estado_idx")]

    def __str__(self):
        return f"Matrícula {str(self.codigo)[:8]} · {self.estudiante.username} · {self.get_estado_display()}"

    @property
    def total(self):
        """Total de la matrícula (usa la anotación si existe)."""
        anotado = getattr(self, "total_anotado", None)
        if anotado is not None:
            return anotado
        return self.detalles.aggregate(t=Sum("costo_matricula"))["t"] or 0


# ============================================================
# DETALLE DE MATRÍCULA (COSTO CONGELADO)
# costo_matricula es un hecho histórico: lo que se pagó ese día,
# aunque el curso cambie de precio después.
# ============================================================
class DetalleMatricula(models.Model):
    """Curso incluido en una matrícula con su costo congelado."""

    matricula = models.ForeignKey(
        Matricula, verbose_name="matrícula", on_delete=models.PROTECT, related_name="detalles"
    )
    curso = models.ForeignKey(
        "cursos.Curso", verbose_name="curso", on_delete=models.PROTECT, related_name="detalles_matricula"
    )
    costo_matricula = models.DecimalField("costo congelado (CLP)", max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "detalle de matrícula"
        verbose_name_plural = "detalles de matrícula"
        ordering = ["matricula", "curso__titulo"]
        constraints = [
            models.UniqueConstraint(fields=["matricula", "curso"], name="detalle_curso_unico_por_matricula"),
            models.CheckConstraint(
                condition=models.Q(costo_matricula__gt=0), name="detalle_costo_positivo"
            ),
        ]

    def __str__(self):
        return f"{self.curso.titulo} · {self.matricula}"


# ============================================================
# INSCRIPCIÓN OFICIAL
# Una por detalle (1 a 1). Estudiante y curso se obtienen por el
# detalle (detalle.matricula.estudiante / detalle.curso): 3FN.
# ============================================================
class Inscripcion(models.Model):
    """Inscripción oficial del estudiante en un curso."""

    detalle = models.OneToOneField(
        DetalleMatricula, verbose_name="detalle", on_delete=models.PROTECT, related_name="inscripcion"
    )
    codigo = models.UUIDField("código de inscripción", unique=True, default=uuid.uuid4, editable=False)
    emitida_en = models.DateTimeField("emitida en", auto_now_add=True)
    activa = models.BooleanField("activa", default=True, db_index=True)

    class Meta:
        verbose_name = "inscripción"
        verbose_name_plural = "inscripciones"
        ordering = ["-emitida_en"]

    def __str__(self):
        return f"Inscripción {self.codigo}"

    @property
    def estudiante(self):
        """Estudiante inscrito (derivado del detalle)."""
        return self.detalle.matricula.estudiante

    @property
    def curso(self):
        """Curso inscrito (derivado del detalle)."""
        return self.detalle.curso


# ============================================================
# HISTORIAL DE ESTADOS (AUDITORÍA)
# ============================================================
class HistorialEstadoMatricula(models.Model):
    """Registro de cada transición de estado de una matrícula."""

    matricula = models.ForeignKey(
        Matricula, verbose_name="matrícula", on_delete=models.PROTECT, related_name="historial"
    )
    estado_anterior = models.CharField(
        "estado anterior", max_length=12, choices=EstadoMatricula.choices, null=True, blank=True
    )
    estado_nuevo = models.CharField("estado nuevo", max_length=12, choices=EstadoMatricula.choices)
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="cambiado por",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cambios_de_estado",
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    observacion = models.CharField("observación", max_length=255, blank=True)

    class Meta:
        verbose_name = "historial de estado"
        verbose_name_plural = "historial de estados"
        ordering = ["fecha", "id"]

    def __str__(self):
        anterior = self.estado_anterior or "—"
        return f"{anterior} → {self.estado_nuevo} ({self.matricula})"
