# ============================================================
# CARRO/MODELS.PY / CARRO DE MATRÍCULA PERSISTENTE
# CarroMatricula tiene relación 1 a 1 con el estudiante y vive en
# PostgreSQL (nunca en sesión, cookies ni localStorage), por eso
# sobrevive al logout y al cambio de dispositivo.
# ItemCarroMatricula no guarda el costo: se lee del curso (3FN).
# ============================================================
from django.conf import settings
from django.db import models
from django.db.models import Sum


# ============================================================
# CARRO DE MATRÍCULA (1 A 1 CON EL ESTUDIANTE)
# ============================================================
class CarroMatricula(models.Model):
    """Carro persistente de un estudiante."""

    estudiante = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="carro_matricula",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "carro de matrícula"
        verbose_name_plural = "carros de matrícula"
        ordering = ["estudiante__username"]

    def __str__(self):
        return f"Carro de {self.estudiante.username}"

    # ============================================================
    # PROPIEDADES CALCULADAS (el total nunca se guarda: 3FN)
    # ============================================================
    @property
    def items_activos(self):
        """Ítems vigentes del carro con su curso y área."""
        return self.items.filter(activo=True).select_related("curso", "curso__area")

    @property
    def total(self):
        """Suma de los costos vigentes de los cursos activos del carro."""
        return self.items_activos.aggregate(t=Sum("curso__costo_matricula"))["t"] or 0

    @property
    def cantidad_cursos(self):
        """Cantidad de cursos activos en el carro."""
        return self.items.filter(activo=True).count()


# ============================================================
# ÍTEM DEL CARRO
# UniqueConstraint(carro, curso): el mismo curso no puede estar dos
# veces en el carro. Quitar = activo=False (se reactiva si se vuelve
# a agregar). Cada ítem representa un cupo a reservar.
# ============================================================
class ItemCarroMatricula(models.Model):
    """Curso agregado al carro de un estudiante."""

    carro = models.ForeignKey(
        CarroMatricula, verbose_name="carro", on_delete=models.CASCADE, related_name="items"
    )
    curso = models.ForeignKey(
        "cursos.Curso", verbose_name="curso", on_delete=models.PROTECT, related_name="items_carro"
    )
    activo = models.BooleanField("activo", default=True, db_index=True)
    agregado_en = models.DateTimeField("agregado en", auto_now=True)

    class Meta:
        verbose_name = "ítem del carro"
        verbose_name_plural = "ítems del carro"
        ordering = ["-agregado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["carro", "curso"],
                name="curso_unico_por_carro",
                violation_error_message="Este curso ya está en tu carro de matrícula.",
            ),
        ]

    def __str__(self):
        return f"{self.curso.titulo} en {self.carro}"
