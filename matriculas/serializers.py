# ============================================================
# MATRICULAS/SERIALIZERS.PY / MATRÍCULAS, INSCRIPCIONES E HISTORIAL
# La matrícula se muestra con sus detalles (costo congelado), sus
# inscripciones UUID, el total calculado y el historial de estados.
# ============================================================
from rest_framework import serializers

from usuarios.serializers import UsuarioResumenSerializer

from .models import DetalleMatricula, EstadoMatricula, HistorialEstadoMatricula, Inscripcion, Matricula
from .servicios import transiciones_disponibles


class InscripcionEnDetalleSerializer(serializers.ModelSerializer):
    """Inscripción oficial asociada a un detalle."""

    class Meta:
        model = Inscripcion
        fields = ["codigo", "activa", "emitida_en"]
        read_only_fields = fields


class DetalleMatriculaSerializer(serializers.ModelSerializer):
    """Curso de la matrícula con su costo congelado e inscripción."""

    curso_id = serializers.IntegerField(source="curso.id", read_only=True)
    curso_titulo = serializers.CharField(source="curso.titulo", read_only=True)
    area = serializers.CharField(source="curso.area.nombre", read_only=True)
    inscripcion = serializers.SerializerMethodField()

    class Meta:
        model = DetalleMatricula
        fields = ["id", "curso_id", "curso_titulo", "area", "costo_matricula", "inscripcion"]
        read_only_fields = fields

    def get_inscripcion(self, obj) -> dict | None:
        inscripcion = getattr(obj, "inscripcion", None)
        return InscripcionEnDetalleSerializer(inscripcion).data if inscripcion else None


class HistorialSerializer(serializers.ModelSerializer):
    """Fila de auditoría de estados."""

    cambiado_por = serializers.CharField(source="cambiado_por.username", read_only=True, default=None)

    class Meta:
        model = HistorialEstadoMatricula
        fields = ["estado_anterior", "estado_nuevo", "cambiado_por", "fecha", "observacion"]
        read_only_fields = fields


class MatriculaSerializer(serializers.ModelSerializer):
    """Matrícula completa."""

    estudiante = UsuarioResumenSerializer(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    detalles = DetalleMatriculaSerializer(many=True, read_only=True)
    historial = HistorialSerializer(many=True, read_only=True)
    transiciones_permitidas = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        fields = [
            "id", "codigo", "estudiante", "estado", "estado_display", "total", "creada_en",
            "pagada_en", "actualizada_en", "transiciones_permitidas", "detalles", "historial",
        ]
        read_only_fields = fields

    def get_transiciones_permitidas(self, obj) -> list[str]:
        return transiciones_disponibles(obj.estado)


class CambioEstadoSerializer(serializers.Serializer):
    """Cuerpo de PATCH /api/matriculas/{id}/estado/."""

    estado = serializers.ChoiceField(
        choices=EstadoMatricula.choices,
        error_messages={"invalid_choice": "«{input}» no es un estado válido (PENDIENTE, PAGADO, COMPLETADO, CANCELADO)."},
    )
    observacion = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")


class InscripcionSerializer(serializers.ModelSerializer):
    """Inscripción oficial con estudiante, curso y matrícula derivados del detalle."""

    estudiante = UsuarioResumenSerializer(source="detalle.matricula.estudiante", read_only=True)
    curso_id = serializers.IntegerField(source="detalle.curso.id", read_only=True)
    curso_titulo = serializers.CharField(source="detalle.curso.titulo", read_only=True)
    matricula_codigo = serializers.UUIDField(source="detalle.matricula.codigo", read_only=True)
    matricula_estado = serializers.CharField(source="detalle.matricula.estado", read_only=True)

    class Meta:
        model = Inscripcion
        fields = [
            "id", "codigo", "activa", "emitida_en", "estudiante", "curso_id", "curso_titulo",
            "matricula_codigo", "matricula_estado",
        ]
        read_only_fields = fields
