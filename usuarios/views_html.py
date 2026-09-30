# ============================================================
# USUARIOS/VIEWS_HTML.PY / GESTIÓN DE USUARIOS EN EL PANEL
# CRUD con elección de rol, contraseña con set_password y baja
# lógica (is_active=False). La ficha del estudiante muestra su carro
# persistido y sus matrículas.
# ============================================================
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from carro.servicios import obtener_carro
from core.utilidades import cambiar_activo_con_confirmacion, filtrar_listado, obtener_o_redirigir, paginar
from matriculas.models import Matricula

from .forms import UsuarioForm
from .models import Rol, Usuario


def usuario_lista(request):
    """Listado de usuarios con buscador, filtro de estado y de rol."""
    usuarios, texto, estado = filtrar_listado(
        request, Usuario.objects.all(), ["username", "first_name", "last_name", "email", "rut"], "is_active"
    )
    rol = request.GET.get("rol", "")
    if rol in Rol.values:
        usuarios = usuarios.filter(rol=rol)
    return render(request, "usuarios/usuario_lista.html", {
        "pagina": paginar(request, usuarios.order_by("rol", "username")),
        "q": texto, "estado": estado, "rol": rol, "roles": Rol.choices,
    })


def usuario_crear(request):
    """Formulario de nuevo usuario (con rol y contraseña)."""
    form = UsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        messages.success(request, f"Usuario «{usuario.username}» creado como {usuario.get_rol_display()}.")
        return redirect("panel_usuario_detalle", pk=usuario.pk)
    return render(request, "usuarios/usuario_form.html", {"form": form, "titulo": "Nuevo usuario"})


def usuario_detalle(request, pk):
    """Ficha del usuario; si es estudiante, muestra su carro y matrículas."""
    usuario, redireccion = obtener_o_redirigir(request, Usuario, pk=pk)
    if redireccion:
        return redireccion
    contexto = {"usuario_obj": usuario}
    if usuario.es_estudiante:
        contexto["carro"] = obtener_carro(usuario)
        contexto["matriculas"] = Matricula.objects.con_total().filter(estudiante=usuario)
    return render(request, "usuarios/usuario_detalle.html", contexto)


def usuario_editar(request, pk):
    """Formulario de edición (contraseña opcional)."""
    usuario, redireccion = obtener_o_redirigir(request, Usuario, pk=pk)
    if redireccion:
        return redireccion
    form = UsuarioForm(request.POST or None, instance=usuario)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Usuario «{usuario.username}» actualizado.")
        return redirect("panel_usuario_detalle", pk=usuario.pk)
    return render(request, "usuarios/usuario_form.html", {
        "form": form, "titulo": f"Editar usuario: {usuario.username}", "usuario_obj": usuario,
    })


def _cambiar_usuario(request, pk, activar):
    usuario, redireccion = obtener_o_redirigir(request, Usuario, pk=pk)
    if redireccion:
        return redireccion
    advertencia = "" if activar else "El usuario no podrá iniciar sesión en la API. Su carro y sus matrículas se conservan."
    return cambiar_activo_con_confirmacion(
        request, usuario, activar, reverse("panel_usuarios") + "?estado=todos",
        reverse("panel_usuario_detalle", args=[usuario.pk]),
        [("Panel", reverse("panel")), ("Usuarios", reverse("panel_usuarios"))],
        campo="is_active", advertencia=advertencia,
    )


def usuario_desactivar(request, pk):
    """Baja lógica del usuario (is_active=False)."""
    return _cambiar_usuario(request, pk, activar=False)


def usuario_reactivar(request, pk):
    """Reactiva un usuario."""
    return _cambiar_usuario(request, pk, activar=True)
