# ============================================================
# CORE/MIXINS.PY / BAJA LÓGICA Y REACTIVACIÓN PARA VIEWSETS
# Nada de negocio se borra físicamente: DELETE marca el registro
# como inactivo y POST .../reactivar/ lo vuelve a activar.
# Los listados públicos solo ven activos; el coordinador puede
# ver inactivos con ?incluir_inactivos=true.
# ============================================================
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from usuarios.permisos import EsCoordinador


class BajaLogicaMixin:
    """Reemplaza el borrado físico por activo=False y agrega /reactivar/."""

    campo_activo = "activo"
    nombre_recurso = "registro"

    # ============================================================
    # ¿QUIÉN PUEDE VER INACTIVOS?
    # El coordinador los ve en detalle/edición siempre y en el
    # listado solo si pide ?incluir_inactivos=true.
    # ============================================================
    def es_coordinador(self):
        return EsCoordinador().has_permission(self.request, self)

    def incluir_inactivos(self):
        if not self.es_coordinador():
            return False
        if getattr(self, "action", None) != "list":
            return True
        return self.request.query_params.get("incluir_inactivos", "").lower() in ("true", "1", "si", "sí")

    def filtrar_activos(self, queryset):
        if self.incluir_inactivos():
            return queryset
        return queryset.filter(**{self.campo_activo: True})

    # ============================================================
    # DELETE = BAJA LÓGICA
    # ============================================================
    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        setattr(instancia, self.campo_activo, False)
        instancia.save(update_fields=[self.campo_activo])
        return Response(
            {"mensaje": f"{self.nombre_recurso.capitalize()} desactivado correctamente (baja lógica).",
             "id": instancia.pk, self.campo_activo: False},
            status=status.HTTP_200_OK,
        )

    # ============================================================
    # REACTIVAR
    # ============================================================
    @action(detail=True, methods=["post"])
    def reactivar(self, request, *args, **kwargs):
        instancia = self.get_object()
        setattr(instancia, self.campo_activo, True)
        instancia.save(update_fields=[self.campo_activo])
        return Response(
            {"mensaje": f"{self.nombre_recurso.capitalize()} reactivado correctamente.",
             "id": instancia.pk, self.campo_activo: True},
            status=status.HTTP_200_OK,
        )
