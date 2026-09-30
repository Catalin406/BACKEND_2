# ============================================================
# CARRO/SERVICIOS.PY / LÓGICA DE NEGOCIO DEL CARRO DE MATRÍCULA
# agregar_curso, quitar_curso y vaciar_carro son usadas tanto por la
# API REST como por las vistas HTML, para que las reglas sean
# idénticas en ambos canales. Agregar al carro NO descuenta cupos:
# solo informa si el curso está agotado. El descuento real ocurre al
# confirmar (matriculas/servicios.py).
# ============================================================
from django.db import IntegrityError, transaction
from rest_framework import status

from core.excepciones import ErrorDeNegocio
from cursos.models import Curso

from .models import CarroMatricula, ItemCarroMatricula


# ============================================================
# EXCEPCIONES DEL CARRO
# ============================================================
class CursoDuplicadoError(ErrorDeNegocio):
    """El curso ya está activo en el carro."""

    mensaje_por_defecto = "Este curso ya está en tu carro de matrícula."


class CursoNoDisponibleError(ErrorDeNegocio):
    """El curso no existe, está inactivo o agotado."""

    mensaje_por_defecto = "El curso no está disponible para matrícula."


class CursoYaInscritoEnCarroError(ErrorDeNegocio):
    """El estudiante ya tiene una inscripción activa en el curso."""

    mensaje_por_defecto = "Ya tienes una inscripción activa en este curso."


class ItemNoEncontradoError(ErrorDeNegocio):
    """El curso no está en el carro."""

    codigo_http = status.HTTP_404_NOT_FOUND
    mensaje_por_defecto = "Este curso no está en tu carro de matrícula."


class NoEsEstudianteError(ErrorDeNegocio):
    """Solo los estudiantes tienen carro de matrícula."""

    codigo_http = status.HTTP_403_FORBIDDEN
    mensaje_por_defecto = "Solo los estudiantes tienen carro de matrícula."


# ============================================================
# OBTENER (O CREAR) EL CARRO 1 A 1
# La señal post_save ya lo crea; get_or_create es una red de
# seguridad para usuarios antiguos o cambios de rol.
# ============================================================
def obtener_carro(estudiante):
    """Devuelve el carro persistente del estudiante."""
    if not estudiante.es_estudiante:
        raise NoEsEstudianteError()
    carro, _ = CarroMatricula.objects.get_or_create(estudiante=estudiante)
    return carro


def _obtener_curso(curso):
    """Acepta una instancia de Curso o su id."""
    if isinstance(curso, Curso):
        return curso
    try:
        return Curso.objects.select_related("area").get(pk=int(curso))
    except (Curso.DoesNotExist, TypeError, ValueError):
        raise CursoNoDisponibleError("El curso indicado no existe.")


# ============================================================
# AGREGAR CURSO
# Reglas: curso activo, con cupos (informativo), sin inscripción
# activa del estudiante y sin duplicados en el carro. Si el ítem
# existía inactivo, se reactiva (el UniqueConstraint impide filas
# duplicadas).
# ============================================================
@transaction.atomic
def agregar_curso(estudiante, curso):
    """Agrega un curso al carro del estudiante y devuelve el ítem."""
    from matriculas.models import Inscripcion

    carro = obtener_carro(estudiante)
    CarroMatricula.objects.select_for_update().filter(pk=carro.pk).first()
    curso = _obtener_curso(curso)

    if not curso.activo or not curso.area.activo:
        raise CursoNoDisponibleError(f"El curso «{curso.titulo}» no está activo.")
    if curso.cupos_disponibles < 1:
        raise CursoNoDisponibleError(
            f"El curso «{curso.titulo}» no tiene cupos disponibles.",
            detalle={"curso_id": curso.id, "cupos_disponibles": curso.cupos_disponibles},
        )
    ya_inscrito = Inscripcion.objects.filter(
        activa=True, detalle__curso=curso, detalle__matricula__estudiante=estudiante
    ).exists()
    if ya_inscrito:
        raise CursoYaInscritoEnCarroError(f"Ya tienes una inscripción activa en «{curso.titulo}».")

    item = ItemCarroMatricula.objects.filter(carro=carro, curso=curso).first()
    if item and item.activo:
        raise CursoDuplicadoError(detalle={"curso_id": curso.id, "titulo": curso.titulo})
    if item:
        item.activo = True
        item.save(update_fields=["activo", "agregado_en"])
    else:
        try:
            with transaction.atomic():
                item = ItemCarroMatricula.objects.create(carro=carro, curso=curso)
        except IntegrityError:
            raise CursoDuplicadoError(detalle={"curso_id": curso.id, "titulo": curso.titulo})
    carro.save(update_fields=["actualizado_en"])
    return item


# ============================================================
# QUITAR CURSO (BAJA LÓGICA DEL ÍTEM)
# ============================================================
@transaction.atomic
def quitar_curso(estudiante, curso_id):
    """Marca el ítem del curso como inactivo."""
    carro = obtener_carro(estudiante)
    actualizados = ItemCarroMatricula.objects.filter(carro=carro, curso_id=curso_id, activo=True).update(
        activo=False
    )
    if not actualizados:
        raise ItemNoEncontradoError()
    carro.save(update_fields=["actualizado_en"])
    return actualizados


# ============================================================
# VACIAR CARRO (TODOS LOS ÍTEMS A activo=False)
# ============================================================
@transaction.atomic
def vaciar_carro(estudiante):
    """Inactiva todos los ítems del carro y devuelve cuántos había."""
    carro = obtener_carro(estudiante)
    cantidad = carro.items.filter(activo=True).update(activo=False)
    carro.save(update_fields=["actualizado_en"])
    return cantidad
