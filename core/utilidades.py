# ============================================================
# CORE/UTILIDADES.PY / AYUDANTES COMPARTIDOS DE LAS VISTAS HTML
# obtener_o_redirigir reemplaza a get_object_or_404: si el objeto no
# existe, redirige a la pantalla de redirección con un mensaje en
# vez de mostrar un 404. También incluye paginación y el filtro
# estándar "buscar + activos/inactivos" de los listados del panel.
# ============================================================
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.shortcuts import redirect, render
from django.urls import reverse


# ============================================================
# OBTENER O REDIRIGIR (SIN 404)
# ============================================================
def obtener_o_redirigir(request, modelo_o_queryset, mensaje=None, **filtros):
    """Devuelve (objeto, None) o (None, redirección a la pantalla de aviso)."""
    if isinstance(modelo_o_queryset, QuerySet):
        queryset = modelo_o_queryset
    else:
        queryset = modelo_o_queryset._default_manager.all()
    try:
        objeto = queryset.filter(**filtros).first()
    except (ValueError, TypeError, ValidationError):
        objeto = None
    if objeto is not None:
        return objeto, None
    nombre = queryset.model._meta.verbose_name
    messages.warning(request, mensaje or f"El registro de {nombre} que buscas no existe.")
    destino = f"{reverse('no_encontrado')}?{urlencode({'ruta': request.path})}"
    return None, redirect(destino)


# ============================================================
# PAGINACIÓN
# ============================================================
def paginar(request, queryset, por_pagina=10):
    """Devuelve la página solicitada (?page=) del queryset."""
    return Paginator(queryset, por_pagina).get_page(request.GET.get("page"))


# ============================================================
# BÚSQUEDA + FILTRO ACTIVOS/INACTIVOS DEL PANEL
# ?q=texto&estado=activos|inactivos|todos
# ============================================================
def filtrar_listado(request, queryset, campos_busqueda, campo_activo="activo"):
    """Aplica el buscador y el filtro de estado; devuelve (queryset, q, estado)."""
    texto = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "activos")
    if texto:
        condicion = Q()
        for campo in campos_busqueda:
            condicion |= Q(**{f"{campo}__icontains": texto})
        queryset = queryset.filter(condicion)
    if estado == "activos":
        queryset = queryset.filter(**{campo_activo: True})
    elif estado == "inactivos":
        queryset = queryset.filter(**{campo_activo: False})
    else:
        estado = "todos"
    return queryset, texto, estado


# ============================================================
# BAJA LÓGICA / REACTIVACIÓN CON CONFIRMACIÓN
# GET muestra core/confirmar.html; POST cambia el campo activo.
# Nunca se ejecuta un DELETE en la base de datos.
# ============================================================
def cambiar_activo_con_confirmacion(request, objeto, activar, url_destino, url_cancelar, migas,
                                    campo="activo", advertencia=""):
    """Desactiva o reactiva 'objeto' tras confirmar; devuelve la respuesta HTTP."""
    nombre = objeto._meta.verbose_name
    accion = "reactivar" if activar else "desactivar"
    if request.method == "POST":
        setattr(objeto, campo, activar)
        objeto.save(update_fields=[campo])
        verbo = "reactivado" if activar else "desactivado"
        messages.success(request, f"Registro de {nombre} «{objeto}» {verbo} correctamente.")
        return redirect(url_destino)
    contexto = {
        "titulo": f"{accion.capitalize()} {nombre}",
        "objeto": objeto,
        "nombre_modelo": nombre,
        "activar": activar,
        "advertencia": advertencia,
        "url_cancelar": url_cancelar,
        "migas": migas,
    }
    return render(request, "core/confirmar.html", contexto)
