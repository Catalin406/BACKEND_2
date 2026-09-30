# ============================================================
# CARRO/SERIALIZERS.PY / REPRESENTACIÓN DEL CARRO DE MATRÍCULA
# Muestra los cursos activos con área, fechas, costo vigente y
# cupos disponibles, más el total y la cantidad de cursos
# (calculados, nunca guardados).
# ============================================================
from rest_framework import serializers

from cursos.serializers import AreaResumenSerializer
from cursos.models import Curso

from .models import CarroMatricula, ItemCarroMatricula


class CursoEnCarroSerializer(serializers.ModelSerializer):
    """Datos del curso relevantes para decidir la matrícula."""

    area = AreaResumenSerializer(read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    modalidad_display = serializers.CharField(source="get_modalidad_display", read_only=True)

    class Meta:
        model = Curso
        fields = [
            "id", "titulo", "area", "tipo", "tipo_display", "modalidad", "modalidad_display",
            "fecha_inicio", "fecha_termino", "costo_matricula", "cupos_disponibles", "cupos_maximos", "activo",
        ]
        read_only_fields = fields


class ItemCarroSerializer(serializers.ModelSerializer):
    """Ítem del carro con su curso anidado."""

    curso = CursoEnCarroSerializer(read_only=True)

    class Meta:
        model = ItemCarroMatricula
        fields = ["id", "curso", "agregado_en"]
        read_only_fields = fields


class CarroSerializer(serializers.ModelSerializer):
    """Carro completo del estudiante."""

    estudiante = serializers.CharField(source="estudiante.username", read_only=True)
    items = serializers.SerializerMethodField()
    total = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    cantidad_cursos = serializers.IntegerField(read_only=True)

    class Meta:
        model = CarroMatricula
        fields = ["id", "estudiante", "cantidad_cursos", "total", "items", "creado_en", "actualizado_en"]
        read_only_fields = fields

    def get_items(self, obj) -> list[dict]:
        return ItemCarroSerializer(obj.items_activos, many=True).data


class AgregarCursoSerializer(serializers.Serializer):
    """Cuerpo de POST /api/carro-matricula/."""

    curso = serializers.IntegerField(min_value=1, help_text="Id del curso a agregar.")
