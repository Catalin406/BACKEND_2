# ============================================================
# MATRICULAS/VIEWS_HTML.PY / PANEL DE MATRÍCULAS E INSCRIPCIONES
# Listado filtrable (MatriculaFilter), detalle con costo congelado,
# inscripciones UUID e historial, y botones de cambio de estado que
# llaman a cambiar_estado_matricula (misma lógica que la API).
# ============================================================
from django.contrib import messages
from django.shortcuts import redirect, render

from core.excepciones import ErrorDeNegocio
from core.forms import estilizar_filtro
from core.utilidades import obtener_o_redirigir, paginar

from . import servicios
from .filtros import InscripcionFilter, MatriculaFilter
from .forms import CambioEstadoForm
from .models import EstadoMatricula, Inscripcion, Matricula


# ============================================================
# LISTADO DE MATRÍCULAS
# ============================================================
def matricula_lista(request):
    """Matrículas con filtro por estado, estudiante, curso y fechas."""
    base = Matricula.objects.con_total().select_related("estudiante").order_by("-creada_en")
    filtro = MatriculaFilter(request.GET or None, queryset=base)
    estilizar_filtro(filtro.form)
    matriculas = filtro.qs if filtro.is_bound else base
    return render(request, "matriculas/matricula_lista.html", {
        "filtro": filtro, "pagina": paginar(request, matriculas), "total": matriculas.count(),
    })


# ============================================================
# DETALLE DE MATRÍCULA
# ============================================================
def matricula_detalle(request, pk):
    """Cursos (costo congelado), total, inscripciones e historial."""
    matricula, redireccion = obtener_o_redirigir(
        request,
        Matricula.objects.con_total().select_related("estudiante").prefetch_related(
            "detalles__curso__area", "detalles__inscripcion", "historial__cambiado_por"
        ),
        pk=pk,
    )
    if redireccion:
        return redireccion
    transiciones = servicios.transiciones_disponibles(matricula.estado)
    return render(request, "matriculas/matricula_detalle.html", {
        "matricula": matricula,
        "puede_completar": EstadoMatricula.COMPLETADO in transiciones,
        "puede_cancelar": EstadoMatricula.CANCELADO in transiciones,
        "estados": EstadoMatricula,
    })


# ============================================================
# CAMBIO DE ESTADO (POST)
# ============================================================
def matricula_cambiar_estado(request, pk):
    """Marca completada o cancela (liberando cupos) una matrícula."""
    matricula, redireccion = obtener_o_redirigir(request, Matricula, pk=pk)
    if redireccion:
        return redireccion
    if request.method == "POST":
        form = CambioEstadoForm(request.POST)
        if form.is_valid():
            nuevo = form.cleaned_data["estado"]
            anterior = matricula.estado
            try:
                servicios.cambiar_estado_matricula(matricula, nuevo, None, form.cleaned_data["observacion"])
                texto = EstadoMatricula(nuevo).label
                libero = nuevo == EstadoMatricula.CANCELADO and anterior == EstadoMatricula.PAGADO
                extra = " Los cupos de sus cursos fueron liberados." if libero else ""
                messages.success(request, f"La matrícula pasó a {texto}.{extra}")
            except ErrorDeNegocio as error:
                messages.error(request, error.mensaje)
        else:
            messages.error(request, "El estado solicitado no es válido.")
    return redirect("panel_matricula_detalle", pk=matricula.pk)


# ============================================================
# INSCRIPCIONES OFICIALES
# ============================================================
def inscripcion_lista(request):
    """Inscripciones con código UUID, filtrables por curso y estado."""
    base = Inscripcion.objects.select_related(
        "detalle__curso", "detalle__matricula__estudiante"
    ).order_by("-emitida_en")
    filtro = InscripcionFilter(request.GET or None, queryset=base)
    estilizar_filtro(filtro.form)
    inscripciones = filtro.qs if filtro.is_bound else base
    return render(request, "matriculas/inscripcion_lista.html", {
        "filtro": filtro, "pagina": paginar(request, inscripciones), "total": inscripciones.count(),
    })
