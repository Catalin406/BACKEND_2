# ============================================================
# CARRO/VIEWS_HTML.PY / PANEL DE CARROS DE MATRÍCULA
# "Ver carro de: [estudiante]" (?estudiante=<id>). Permite agregar,
# quitar, vaciar y confirmar llamando a carro/servicios.py y
# matriculas/servicios.py: mismas reglas de cupos y concurrencia que
# la API. Los errores de negocio se muestran como mensajes.
# ============================================================
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import format_html

from core.excepciones import ErrorDeNegocio
from core.utilidades import obtener_o_redirigir
from matriculas import servicios as servicios_matricula
from usuarios.models import Rol, Usuario
from usuarios.permisos import solo_coordinador_para_escribir

from . import servicios
from .forms import AgregarCursoCarroForm, SeleccionEstudianteForm

ESTUDIANTES = Usuario.objects.filter(rol=Rol.ESTUDIANTE)


def _url_carro(estudiante_id):
    return f"{reverse('panel_carros')}?estudiante={estudiante_id}"


def _obtener_estudiante(request, estudiante_id):
    return obtener_o_redirigir(
        request, ESTUDIANTES, pk=estudiante_id, mensaje="El estudiante seleccionado no existe."
    )


# ============================================================
# VER CARRO DE UN ESTUDIANTE
# ============================================================
def carro_panel(request):
    """Selector de estudiante y carro persistido del seleccionado."""
    estudiante = carro = None
    estudiante_id = request.GET.get("estudiante")
    if estudiante_id:
        estudiante, redireccion = _obtener_estudiante(request, estudiante_id)
        if redireccion:
            return redireccion
        carro = servicios.obtener_carro(estudiante)
    selector = SeleccionEstudianteForm(initial={"estudiante": estudiante})
    estudiantes = ESTUDIANTES.filter(is_active=True).annotate(
        n_items=Count("carro_matricula__items", filter=Q(carro_matricula__items__activo=True))
    ).order_by("username")
    return render(request, "carro/carro_panel.html", {
        "selector": selector,
        "estudiante": estudiante,
        "carro": carro,
        "items": carro.items_activos if carro else [],
        "form_agregar": AgregarCursoCarroForm(),
        "estudiantes": estudiantes,
    })


# ============================================================
# ACCIONES SOBRE EL CARRO (SOLO POST)
# ============================================================
@solo_coordinador_para_escribir
def carro_agregar(request, estudiante_id):
    """Agrega un curso; muestra el error si ya estaba o no hay cupos."""
    estudiante, redireccion = _obtener_estudiante(request, estudiante_id)
    if redireccion:
        return redireccion
    if request.method == "POST":
        form = AgregarCursoCarroForm(request.POST)
        if form.is_valid():
            try:
                item = servicios.agregar_curso(estudiante, form.cleaned_data["curso"])
                messages.success(request, f"Curso «{item.curso.titulo}» agregado al carro de {estudiante.username}.")
            except ErrorDeNegocio as error:
                messages.error(request, error.mensaje)
        else:
            messages.error(request, "Selecciona un curso válido para agregar.")
    return redirect(_url_carro(estudiante.pk))


@solo_coordinador_para_escribir
def carro_quitar(request, estudiante_id, curso_id):
    """Quita un curso del carro (baja lógica del ítem)."""
    estudiante, redireccion = _obtener_estudiante(request, estudiante_id)
    if redireccion:
        return redireccion
    if request.method == "POST":
        try:
            servicios.quitar_curso(estudiante, curso_id)
            messages.success(request, "Curso quitado del carro.")
        except ErrorDeNegocio as error:
            messages.error(request, error.mensaje)
    return redirect(_url_carro(estudiante.pk))


@solo_coordinador_para_escribir
def carro_vaciar(request, estudiante_id):
    """Vacía el carro completo."""
    estudiante, redireccion = _obtener_estudiante(request, estudiante_id)
    if redireccion:
        return redireccion
    if request.method == "POST":
        cantidad = servicios.vaciar_carro(estudiante)
        messages.success(request, f"Carro vaciado: se quitaron {cantidad} cursos.")
    return redirect(_url_carro(estudiante.pk))


@solo_coordinador_para_escribir
def carro_confirmar(request, estudiante_id):
    """Confirma la matrícula (pago simulado) con control de cupos."""
    estudiante, redireccion = _obtener_estudiante(request, estudiante_id)
    if redireccion:
        return redireccion
    if request.method != "POST":
        return redirect(_url_carro(estudiante.pk))
    try:
        matricula = servicios_matricula.confirmar_matricula(
            estudiante, autor=request.user, observacion_pago="Confirmada desde el panel por el coordinador."
        )
    except ErrorDeNegocio as error:
        messages.error(request, error.mensaje)
        return redirect(_url_carro(estudiante.pk))
    messages.success(
        request,
        format_html(
            "Matrícula <strong>{}</strong> confirmada y pagada. Se emitieron {} inscripciones oficiales.",
            str(matricula.codigo)[:8], matricula.detalles.count(),
        ),
    )
    return redirect("panel_matricula_detalle", pk=matricula.pk)
