# ============================================================
# CURSOS/SERIALIZERS.PY / SERIALIZACIÓN DE ÁREAS Y CURSOS
# Lectura: área anidada, etiquetas legibles de tipo y modalidad,
# cupos y duración. Escritura: recibe el id del área y valida
# costo, fechas, cupos y cohorte única con mensajes en español.
# ============================================================
from rest_framework import serializers

from .models import AreaConocimiento, Curso


# ============================================================
# ÁREAS DE CONOCIMIENTO
# ============================================================
class AreaSerializer(serializers.ModelSerializer):
    """Área de conocimiento con la cantidad de cursos activos."""

    cantidad_cursos = serializers.SerializerMethodField()

    class Meta:
        model = AreaConocimiento
        fields = ["id", "nombre", "descripcion", "icono", "activo", "cantidad_cursos", "creado_en", "actualizado_en"]
        read_only_fields = ["id", "activo", "creado_en", "actualizado_en"]

    def get_cantidad_cursos(self, obj) -> int:
        return obj.cursos.filter(activo=True).count()


class AreaResumenSerializer(serializers.ModelSerializer):
    """Área anidada dentro del curso (id + nombre)."""

    class Meta:
        model = AreaConocimiento
        fields = ["id", "nombre", "icono"]
        read_only_fields = fields


# ============================================================
# CURSOS: LECTURA
# ============================================================
class CursoLecturaSerializer(serializers.ModelSerializer):
    """Curso con área anidada y campos calculados."""

    area = AreaResumenSerializer(read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    modalidad_display = serializers.CharField(source="get_modalidad_display", read_only=True)
    duracion_dias = serializers.IntegerField(read_only=True)
    cupos_ocupados = serializers.IntegerField(read_only=True)

    class Meta:
        model = Curso
        fields = [
            "id", "titulo", "descripcion", "area", "tipo", "tipo_display", "modalidad",
            "modalidad_display", "costo_matricula", "fecha_inicio", "fecha_termino",
            "duracion_dias", "cupos_maximos", "cupos_disponibles", "cupos_ocupados",
            "activo", "creado_en", "actualizado_en",
        ]
        read_only_fields = fields


# ============================================================
# CURSOS: ESCRITURA (SOLO COORDINADOR)
# ============================================================
class CursoEscrituraSerializer(serializers.ModelSerializer):
    """Crea o edita un curso validando las reglas de negocio."""

    area = serializers.PrimaryKeyRelatedField(
        queryset=AreaConocimiento.objects.all(),
        error_messages={
            "does_not_exist": "El área indicada no existe.",
            "incorrect_type": "El área debe indicarse con su id numérico.",
        },
    )

    class Meta:
        model = Curso
        fields = [
            "id", "titulo", "descripcion", "area", "tipo", "modalidad", "costo_matricula",
            "fecha_inicio", "fecha_termino", "cupos_maximos",
        ]
        read_only_fields = ["id"]
        validators = []  # La cohorte única se valida abajo con un mensaje propio.

    def validate_area(self, area):
        if not area.activo:
            raise serializers.ValidationError("El área seleccionada está inactiva.")
        return area

    def validate_costo_matricula(self, valor):
        if valor is None or valor <= 0:
            raise serializers.ValidationError("El costo de matrícula debe ser mayor a 0.")
        return valor

    def validate_cupos_maximos(self, valor):
        if valor < 1:
            raise serializers.ValidationError("El curso debe tener al menos 1 cupo.")
        if self.instance is not None:
            ocupados = self.instance.cupos_ocupados_en_bd()
            if valor < ocupados:
                raise serializers.ValidationError(
                    f"No puedes dejar {valor} cupos máximos: ya hay {ocupados} cupos ocupados por inscripciones activas."
                )
        return valor

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        termino = attrs.get("fecha_termino", getattr(self.instance, "fecha_termino", None))
        titulo = attrs.get("titulo", getattr(self.instance, "titulo", None))
        if inicio and termino and termino < inicio:
            raise serializers.ValidationError(
                {"fecha_termino": "La fecha de término no puede ser anterior a la fecha de inicio."}
            )
        duplicados = Curso.objects.filter(titulo=titulo, fecha_inicio=inicio)
        if self.instance is not None:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise serializers.ValidationError(
                {"fecha_inicio": "Ya existe una cohorte de este curso con la misma fecha de inicio."}
            )
        return attrs
