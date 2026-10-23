# ============================================================
# MATRICULAS/SERVICIOS.PY / CONFIRMACIÓN, CUPOS, ESTADOS E INSCRIPCIONES
# Aquí vive la regla de negocio más crítica del sistema: los cupos.
#  - confirmar_matricula(): valida y descuenta cupos de forma atómica
#    bajo bloqueo de filas (SELECT ... FOR UPDATE), crea la matrícula
#    PAGADA, congela costos y emite inscripciones con UUID.
#  - cambiar_estado_matricula(): aplica solo transiciones permitidas y
#    libera cupos al cancelar una matrícula pagada.
# La API y las vistas HTML usan estas mismas funciones.
# ============================================================
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status

from carro.models import CarroMatricula
from core.excepciones import ErrorDeNegocio
from cursos.models import Curso

from .models import DetalleMatricula, EstadoMatricula, HistorialEstadoMatricula, Inscripcion, Matricula


# ============================================================
# EXCEPCIONES PROPIAS
# Todas heredan de ErrorDeNegocio: el manejador de la API las
# traduce a JSON y las vistas HTML las muestran como mensajes.
# ============================================================
class CarroVacioError(ErrorDeNegocio):
    """No hay cursos activos en el carro."""

    codigo_http = status.HTTP_400_BAD_REQUEST
    mensaje_por_defecto = "Tu carro de matrícula está vacío: agrega al menos un curso antes de confirmar."


class SinCuposError(ErrorDeNegocio):
    """Uno o más cursos no tienen cupos disponibles (409)."""

    codigo_http = status.HTTP_409_CONFLICT
    mensaje_por_defecto = "Uno o más cursos ya no tienen cupos disponibles."

    def __init__(self, cursos):
        self.cursos = cursos
        titulos = ", ".join(f"«{c['titulo']}»" for c in cursos)
        super().__init__(
            f"No hay cupos disponibles en: {titulos}. Quita esos cursos del carro para continuar.",
            detalle={"cursos_sin_cupo": cursos},
        )


class CursoInactivoError(ErrorDeNegocio):
    """Un curso del carro fue desactivado (409)."""

    codigo_http = status.HTTP_409_CONFLICT
    mensaje_por_defecto = "Uno o más cursos del carro ya no están activos."


class CursoYaInscritoError(ErrorDeNegocio):
    """El estudiante ya tiene inscripción activa en un curso del carro (409)."""

    codigo_http = status.HTTP_409_CONFLICT
    mensaje_por_defecto = "Ya tienes una inscripción activa en uno de los cursos del carro."


class TransicionInvalidaError(ErrorDeNegocio):
    """Cambio de estado no permitido (400)."""

    codigo_http = status.HTTP_400_BAD_REQUEST
    mensaje_por_defecto = "La transición de estado solicitada no está permitida."


# ============================================================
# MÁQUINA DE ESTADOS
# COMPLETADO y CANCELADO son estados finales.
# ============================================================
TRANSICIONES_PERMITIDAS = {
    EstadoMatricula.PENDIENTE: {EstadoMatricula.CANCELADO},
    EstadoMatricula.PAGADO: {EstadoMatricula.COMPLETADO, EstadoMatricula.CANCELADO},
    EstadoMatricula.COMPLETADO: set(),
    EstadoMatricula.CANCELADO: set(),
}


def transiciones_disponibles(estado):
    """Estados a los que puede pasar una matrícula desde 'estado'."""
    return sorted(TRANSICIONES_PERMITIDAS.get(estado, set()))


def _registrar_historial(matricula, anterior, nuevo, usuario, observacion=""):
    """Guarda una fila de auditoría de la transición."""
    return HistorialEstadoMatricula.objects.create(
        matricula=matricula,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        cambiado_por=usuario,
        observacion=observacion[:255],
    )


def _resumen_curso(curso):
    return {"curso_id": curso.id, "titulo": curso.titulo, "cupos_disponibles": curso.cupos_disponibles}


# ============================================================
# CONFIRMAR MATRÍCULA (CHECKOUT CON PAGO SIMULADO)
# Todo ocurre en UNA transacción. Si algo falla se lanza una
# excepción y PostgreSQL revierte todo: no queda matrícula, ningún
# cupo cambia y el carro queda intacto.
# ============================================================
def confirmar_matricula(estudiante, autor=None, observacion_pago="Pago aprobado (simulado)."):
    """Convierte el carro del estudiante en una matrícula PAGADA con inscripciones.

    'autor' es quien queda registrado en el historial (por defecto el propio
    estudiante, como en la API; en el panel es el coordinador con sesión).
    """
    autor = autor or estudiante
    with transaction.atomic():
        # ------------------------------------------------------------
        # 1) Bloqueo del carro: evita dos confirmaciones simultáneas
        #    del mismo estudiante (la segunda espera y lo verá vacío).
        # ------------------------------------------------------------
        carro = CarroMatricula.objects.select_for_update().filter(estudiante=estudiante).first()
        if carro is None:
            raise CarroVacioError()
        ids = list(carro.items.filter(activo=True).values_list("curso_id", flat=True))
        if not ids:
            raise CarroVacioError()

        # ------------------------------------------------------------
        # 2) Bloqueo de los cursos en orden fijo por id (evita
        #    interbloqueos). Si otro estudiante confirma el mismo curso,
        #    esta consulta espera y luego relee los cupos actualizados.
        # ------------------------------------------------------------
        cursos = list(Curso.objects.select_for_update().filter(id__in=ids).order_by("id"))

        # ------------------------------------------------------------
        # 3) Validaciones: curso activo, al menos 1 cupo y sin
        #    inscripción activa previa del mismo estudiante.
        # ------------------------------------------------------------
        inactivos = [_resumen_curso(c) for c in cursos if not c.activo]
        if inactivos:
            raise CursoInactivoError(
                "Estos cursos ya no están activos: "
                + ", ".join(f"«{c['titulo']}»" for c in inactivos)
                + ". Quítalos del carro para continuar.",
                detalle={"cursos_inactivos": inactivos},
            )
        sin_cupo = [_resumen_curso(c) for c in cursos if c.cupos_disponibles < 1]
        if sin_cupo:
            raise SinCuposError(sin_cupo)
        inscritos = set(
            Inscripcion.objects.filter(
                activa=True, detalle__matricula__estudiante=estudiante, detalle__curso_id__in=ids
            ).values_list("detalle__curso_id", flat=True)
        )
        if inscritos:
            repetidos = [_resumen_curso(c) for c in cursos if c.id in inscritos]
            raise CursoYaInscritoError(
                "Ya tienes una inscripción activa en: " + ", ".join(f"«{c['titulo']}»" for c in repetidos) + ".",
                detalle={"cursos_ya_inscritos": repetidos},
            )

        # ------------------------------------------------------------
        # 4) Matrícula PENDIENTE + detalles con el costo congelado.
        # ------------------------------------------------------------
        matricula = Matricula.objects.create(estudiante=estudiante)
        _registrar_historial(matricula, None, EstadoMatricula.PENDIENTE, autor, "Matrícula creada desde el carro.")
        detalles = DetalleMatricula.objects.bulk_create(
            [DetalleMatricula(matricula=matricula, curso=c, costo_matricula=c.costo_matricula) for c in cursos]
        )

        # ------------------------------------------------------------
        # 5) Pago aprobado (simulado): descuento atómico de 1 cupo por
        #    curso con F() y paso a PAGADO. El CheckConstraint de la BD
        #    impide cupos negativos como última barrera.
        # ------------------------------------------------------------
        Curso.objects.filter(id__in=ids).update(cupos_disponibles=F("cupos_disponibles") - 1)
        matricula.estado = EstadoMatricula.PAGADO
        matricula.pagada_en = timezone.now()
        matricula.save(update_fields=["estado", "pagada_en", "actualizada_en"])
        _registrar_historial(
            matricula, EstadoMatricula.PENDIENTE, EstadoMatricula.PAGADO, autor, observacion_pago
        )

        # ------------------------------------------------------------
        # 6) Inscripciones oficiales: una por curso con UUID único.
        # ------------------------------------------------------------
        Inscripcion.objects.bulk_create([Inscripcion(detalle=d) for d in detalles])

        # ------------------------------------------------------------
        # 7) El carro se vacía (baja lógica de sus ítems).
        # ------------------------------------------------------------
        carro.items.filter(activo=True).update(activo=False)
        carro.save(update_fields=["actualizado_en"])

    return matricula


# ============================================================
# CAMBIAR ESTADO (COORDINADOR)
# PAGADO -> CANCELADO libera 1 cupo por curso e inactiva las
# inscripciones, todo bajo bloqueo y en una transacción.
# ============================================================
def cambiar_estado_matricula(matricula, nuevo_estado, usuario, observacion=""):
    """Aplica una transición permitida y la registra en el historial."""
    if nuevo_estado not in EstadoMatricula.values:
        raise TransicionInvalidaError(
            f"El estado «{nuevo_estado}» no existe. Valores válidos: {', '.join(EstadoMatricula.values)}."
        )
    with transaction.atomic():
        matricula = Matricula.objects.select_for_update().get(pk=matricula.pk)
        anterior = matricula.estado
        if nuevo_estado not in TRANSICIONES_PERMITIDAS[anterior]:
            permitidas = [EstadoMatricula(e).label for e in transiciones_disponibles(anterior)]
            sugerencia = (
                f" Desde {EstadoMatricula(anterior).label} solo se puede pasar a: {', '.join(permitidas)}."
                if permitidas
                else f" {EstadoMatricula(anterior).label} es un estado final."
            )
            raise TransicionInvalidaError(
                f"No se puede cambiar una matrícula de {EstadoMatricula(anterior).label} "
                f"a {EstadoMatricula(nuevo_estado).label}.{sugerencia}",
                detalle={"estado_actual": anterior, "estado_solicitado": nuevo_estado,
                         "permitidos": transiciones_disponibles(anterior)},
            )

        # ------------------------------------------------------------
        # Liberación de cupos al cancelar una matrícula pagada.
        # ------------------------------------------------------------
        if anterior == EstadoMatricula.PAGADO and nuevo_estado == EstadoMatricula.CANCELADO:
            ids = list(
                matricula.detalles.filter(inscripcion__activa=True).values_list("curso_id", flat=True)
            )
            list(Curso.objects.select_for_update().filter(id__in=ids).order_by("id"))
            Curso.objects.filter(id__in=ids).update(cupos_disponibles=F("cupos_disponibles") + 1)
            Inscripcion.objects.filter(detalle__matricula=matricula, activa=True).update(activa=False)

        matricula.estado = nuevo_estado
        matricula.save(update_fields=["estado", "actualizada_en"])
        _registrar_historial(matricula, anterior, nuevo_estado, usuario, observacion)
    return matricula
