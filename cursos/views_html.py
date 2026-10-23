# ============================================================
# CURSOS/VIEWS_HTML.PY / PÁGINAS DE OFERTA ACADÉMICA Y GESTIÓN
# Oferta pública (/cursos/) con el mismo CursoFilter de la API y
# CRUD del panel (/panel/areas/, /panel/cursos/) con ModelForm,
# mensajes flash y baja lógica. Sin get_object_or_404: se usa
# obtener_o_redirigir() para no mostrar nunca un 404.
# ============================================================
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse

from core.forms import estilizar_filtro
from core.utilidades import cambiar_activo_con_confirmacion, filtrar_listado, obtener_o_redirigir, paginar
from matriculas.models import Inscripcion
from usuarios.permisos import solo_coordinador_para_escribir

from .filtros import CursoFilter
from .forms import AreaForm, CursoForm
from .models import AreaConocimiento, Curso

ORDENES_OFERTA = {
    "fecha_inicio": "Próximos a iniciar",
    "costo_matricula": "Menor costo",
    "-costo_matricula": "Mayor costo",
    "titulo": "Título (A-Z)",
    "-cupos_disponibles": "Más cupos disponibles",
}


# ============================================================
# OFERTA ACADÉMICA PÚBLICA
# ============================================================
def oferta_lista(request):
    """Listado público con filtros, búsqueda, orden y paginación."""
    base = Curso.objects.filter(activo=True, area__activo=True).select_related("area")
    filtro = CursoFilter(request.GET or None, queryset=base)
    estilizar_filtro(filtro.form)
    cursos = filtro.qs if filtro.is_bound else base
    texto = request.GET.get("q", "").strip()
    if texto:
        cursos = cursos.filter(
            Q(titulo__icontains=texto) | Q(descripcion__icontains=texto) | Q(area__nombre__icontains=texto)
        )
    orden = request.GET.get("orden", "fecha_inicio")
    if orden not in ORDENES_OFERTA:
        orden = "fecha_inicio"
    cursos = cursos.order_by(orden, "titulo")
    return render(request, "cursos/oferta_lista.html", {
        "filtro": filtro,
        "pagina": paginar(request, cursos, 9),
        "total": cursos.count(),
        "q": texto,
        "orden": orden,
        "ordenes": ORDENES_OFERTA,
    })


def oferta_detalle(request, pk):
    """Detalle público de un curso activo."""
    curso, redireccion = obtener_o_redirigir(
        request, Curso.objects.select_related("area").filter(activo=True, area__activo=True), pk=pk,
        mensaje="El curso que buscas no existe o ya no está disponible.",
    )
    if redireccion:
        return redireccion
    relacionados = (
        Curso.objects.filter(area=curso.area, activo=True).exclude(pk=curso.pk).order_by("fecha_inicio")[:3]
    )
    return render(request, "cursos/oferta_detalle.html", {"curso": curso, "relacionados": relacionados})


# ============================================================
# PANEL: ÁREAS DE CONOCIMIENTO
# ============================================================
def area_lista(request):
    """Listado de áreas con buscador y filtro activos/inactivos."""
    areas = AreaConocimiento.objects.annotate(n_cursos=Count("cursos", filter=Q(cursos__activo=True)))
    areas, texto, estado = filtrar_listado(request, areas, ["nombre", "descripcion"])
    return render(request, "cursos/area_lista.html", {
        "pagina": paginar(request, areas.order_by("nombre")), "q": texto, "estado": estado,
    })


@solo_coordinador_para_escribir
def area_crear(request):
    """Formulario de nueva área."""
    form = AreaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        area = form.save()
        messages.success(request, f"Área «{area.nombre}» creada correctamente.")
        return redirect("panel_area_detalle", pk=area.pk)
    return render(request, "cursos/area_form.html", {"form": form, "titulo": "Nueva área"})


def area_detalle(request, pk):
    """Ficha del área con sus cursos."""
    area, redireccion = obtener_o_redirigir(request, AreaConocimiento, pk=pk)
    if redireccion:
        return redireccion
    cursos = area.cursos.order_by("-activo", "fecha_inicio")
    return render(request, "cursos/area_detalle.html", {"area": area, "cursos": cursos})


@solo_coordinador_para_escribir
def area_editar(request, pk):
    """Formulario de edición del área."""
    area, redireccion = obtener_o_redirigir(request, AreaConocimiento, pk=pk)
    if redireccion:
        return redireccion
    form = AreaForm(request.POST or None, instance=area)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Área «{area.nombre}» actualizada.")
        return redirect("panel_area_detalle", pk=area.pk)
    return render(request, "cursos/area_form.html", {"form": form, "titulo": f"Editar área: {area.nombre}", "area": area})


def _cambiar_area(request, pk, activar):
    area, redireccion = obtener_o_redirigir(request, AreaConocimiento, pk=pk)
    if redireccion:
        return redireccion
    advertencia = ""
    if not activar:
        n = area.cursos.filter(activo=True).count()
        if n:
            advertencia = f"Sus {n} cursos activos dejarán de mostrarse en la oferta pública mientras el área esté inactiva."
    return cambiar_activo_con_confirmacion(
        request, area, activar, reverse("panel_areas") + ("?estado=todos"),
        reverse("panel_area_detalle", args=[area.pk]),
        [("Panel", reverse("panel")), ("Áreas", reverse("panel_areas"))],
        advertencia=advertencia,
    )


@solo_coordinador_para_escribir
def area_desactivar(request, pk):
    """Baja lógica del área (activo=False)."""
    return _cambiar_area(request, pk, activar=False)


@solo_coordinador_para_escribir
def area_reactivar(request, pk):
    """Reactiva un área inactiva."""
    return _cambiar_area(request, pk, activar=True)


# ============================================================
# PANEL: CURSOS
# ============================================================
def curso_lista(request):
    """Listado de cursos con buscador, filtro de estado y de área."""
    cursos = Curso.objects.select_related("area")
    cursos, texto, estado = filtrar_listado(request, cursos, ["titulo", "descripcion", "area__nombre"])
    area_id = request.GET.get("area", "")
    if area_id.isdigit():
        cursos = cursos.filter(area_id=area_id)
    return render(request, "cursos/curso_lista.html", {
        "pagina": paginar(request, cursos.order_by("fecha_inicio", "titulo")),
        "q": texto, "estado": estado, "area_id": area_id,
        "areas": AreaConocimiento.objects.order_by("nombre"),
    })


def _guardar_curso(request, form):
    """Guarda el curso capturando la validación de cupos hecha en save()."""
    try:
        return form.save()
    except ValidationError as error:
        for campo, errores in error.message_dict.items():
            form.add_error(campo if campo in form.fields else None, errores)
        return None


@solo_coordinador_para_escribir
def curso_crear(request):
    """Formulario de nuevo curso."""
    form = CursoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        curso = _guardar_curso(request, form)
        if curso:
            messages.success(request, f"Curso «{curso.titulo}» creado con {curso.cupos_maximos} cupos.")
            return redirect("panel_curso_detalle", pk=curso.pk)
    return render(request, "cursos/curso_form.html", {"form": form, "titulo": "Nuevo curso"})


def curso_detalle(request, pk):
    """Ficha del curso con sus inscritos."""
    curso, redireccion = obtener_o_redirigir(request, Curso.objects.select_related("area"), pk=pk)
    if redireccion:
        return redireccion
    inscripciones = (
        Inscripcion.objects.filter(detalle__curso=curso)
        .select_related("detalle__matricula__estudiante")
        .order_by("-activa", "-emitida_en")
    )
    return render(request, "cursos/curso_detalle.html", {"curso": curso, "inscripciones": inscripciones})


@solo_coordinador_para_escribir
def curso_editar(request, pk):
    """Formulario de edición del curso (ajusta cupos disponibles)."""
    curso, redireccion = obtener_o_redirigir(request, Curso, pk=pk)
    if redireccion:
        return redireccion
    form = CursoForm(request.POST or None, instance=curso)
    if request.method == "POST" and form.is_valid():
        curso = _guardar_curso(request, form)
        if curso:
            messages.success(
                request, f"Curso «{curso.titulo}» actualizado. Cupos disponibles: {curso.cupos_disponibles}."
            )
            return redirect("panel_curso_detalle", pk=curso.pk)
    return render(request, "cursos/curso_form.html", {"form": form, "titulo": f"Editar curso: {curso.titulo}", "curso": curso})


def _cambiar_curso(request, pk, activar):
    curso, redireccion = obtener_o_redirigir(request, Curso, pk=pk)
    if redireccion:
        return redireccion
    advertencia = ""
    if not activar:
        advertencia = "El curso dejará de aparecer en la oferta y no podrá agregarse a nuevos carros. Las inscripciones existentes se mantienen."
    return cambiar_activo_con_confirmacion(
        request, curso, activar, reverse("panel_cursos") + "?estado=todos",
        reverse("panel_curso_detalle", args=[curso.pk]),
        [("Panel", reverse("panel")), ("Cursos", reverse("panel_cursos"))],
        advertencia=advertencia,
    )


@solo_coordinador_para_escribir
def curso_desactivar(request, pk):
    """Baja lógica del curso (activo=False)."""
    return _cambiar_curso(request, pk, activar=False)


@solo_coordinador_para_escribir
def curso_reactivar(request, pk):
    """Reactiva un curso inactivo."""
    return _cambiar_curso(request, pk, activar=True)
