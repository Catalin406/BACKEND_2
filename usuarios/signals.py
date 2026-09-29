# ============================================================
# USUARIOS/SIGNALS.PY / CREACIÓN AUTOMÁTICA DEL CARRO
# Cada ESTUDIANTE tiene exactamente un carro de matrícula (1 a 1).
# La señal post_save lo crea al registrar al estudiante (o cuando un
# usuario pasa a ser estudiante), así el carro existe siempre en
# PostgreSQL y nunca depende de la sesión del navegador.
# ============================================================
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Rol, Usuario


@receiver(post_save, sender=Usuario, dispatch_uid="crear_carro_estudiante")
def crear_carro_para_estudiante(sender, instance, created, raw=False, **kwargs):
    """Crea el CarroMatricula del estudiante si aún no existe."""
    if raw or instance.rol != Rol.ESTUDIANTE:
        return
    from carro.models import CarroMatricula

    CarroMatricula.objects.get_or_create(estudiante=instance)
