# ============================================================
# CORE/MANAGEMENT/COMMANDS/SIMULAR_CONCURRENCIA.PY
# DEMOSTRACIÓN DE CONCURRENCIA REAL SOBRE EL ÚLTIMO CUPO
# Crea (o reinicia) un curso de demostración con 1 cupo y dos
# estudiantes de demostración con ese curso en su carro. Dos hilos,
# cada uno con su propia conexión a PostgreSQL, confirman la matrícula
# al mismo tiempo. SELECT ... FOR UPDATE hace que el segundo espere,
# relea cupos_disponibles = 0 y sea rechazado: los cupos nunca quedan
# en -1.
# ============================================================
import threading
import time
from datetime import date

from django.core.management.base import BaseCommand
from django.db import connection

from carro import servicios as servicios_carro
from core.excepciones import ErrorDeNegocio
from cursos.models import AreaConocimiento, Curso, Modalidad, TipoCurso
from matriculas import servicios as servicios_matricula
from matriculas.models import EstadoMatricula, Inscripcion, Matricula
from usuarios.models import Rol, Usuario

TITULO_DEMO = "Curso Demo de Concurrencia"
INICIO_DEMO = date(2026, 12, 1)


class Command(BaseCommand):
    """Dos estudiantes compiten por el último cupo al mismo tiempo."""

    help = "Demuestra que dos confirmaciones simultáneas por el último cupo dejan solo una matrícula PAGADA."

    # ============================================================
    # PREPARACIÓN DEL ESCENARIO (REPETIBLE)
    # ============================================================
    def _preparar(self):
        area, _ = AreaConocimiento.objects.get_or_create(
            nombre="Desarrollo Web", defaults={"icono": "bi-code-slash", "descripcion": "Área de demostración."}
        )
        coordinador = Usuario.objects.filter(rol=Rol.COORDINADOR).first()
        curso = Curso.objects.filter(titulo=TITULO_DEMO, fecha_inicio=INICIO_DEMO).first()
        if curso:
            # Cancela las matrículas de corridas anteriores: libera el cupo con el servicio.
            for matricula in Matricula.objects.filter(detalles__curso=curso, estado=EstadoMatricula.PAGADO):
                servicios_matricula.cambiar_estado_matricula(
                    matricula, EstadoMatricula.CANCELADO, coordinador, "Reinicio de la simulación de concurrencia."
                )
            curso.activo = True
            curso.cupos_maximos = 1
            curso.save()
        else:
            curso = Curso.objects.create(
                titulo=TITULO_DEMO, descripcion="Curso con un único cupo para demostrar el control de concurrencia.",
                area=area, tipo=TipoCurso.TALLER, modalidad=Modalidad.ONLINE, costo_matricula=10000,
                fecha_inicio=INICIO_DEMO, fecha_termino=INICIO_DEMO, cupos_maximos=1,
            )
        estudiantes = []
        for username, nombre in (("demo_ana", "Ana"), ("demo_bruno", "Bruno")):
            estudiante, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@codelab.cl", "first_name": nombre, "last_name": "Demo",
                          "rol": Rol.ESTUDIANTE},
            )
            if creado:
                estudiante.set_password("Demo2026!")
                estudiante.save()
            servicios_carro.vaciar_carro(estudiante)
            servicios_carro.agregar_curso(estudiante, curso)
            estudiantes.append(estudiante)
        return curso, estudiantes

    # ============================================================
    # CARRERA DE DOS HILOS
    # Una barrera libera a ambos hilos en el mismo instante.
    # ============================================================
    def handle(self, *args, **opciones):
        curso, estudiantes = self._preparar()
        self.stdout.write(self.style.MIGRATE_HEADING("Simulación de concurrencia: dos estudiantes, un solo cupo"))
        self.stdout.write(f"  Curso: {curso.titulo} · cupos disponibles antes: {curso.cupos_disponibles}")
        self.stdout.write(f"  Compiten: {estudiantes[0].username} y {estudiantes[1].username}\n")

        barrera = threading.Barrier(len(estudiantes))
        resultados = {}

        def confirmar(estudiante):
            try:
                barrera.wait()
                inicio = time.perf_counter()
                try:
                    matricula = servicios_matricula.confirmar_matricula(estudiante)
                    inscripcion = Inscripcion.objects.get(detalle__matricula=matricula)
                    resultados[estudiante.username] = ("OK", matricula, inscripcion, time.perf_counter() - inicio)
                except ErrorDeNegocio as error:
                    resultados[estudiante.username] = ("RECHAZADO", error, None, time.perf_counter() - inicio)
            finally:
                connection.close()  # cada hilo cierra su propia conexión a PostgreSQL

        hilos = [threading.Thread(target=confirmar, args=(e,), name=e.username) for e in estudiantes]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        # ------------------------------------------------------------
        # Reporte
        # ------------------------------------------------------------
        for estudiante in estudiantes:
            estado, dato, inscripcion, segundos = resultados[estudiante.username]
            if estado == "OK":
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ {estudiante.username}: matrícula {dato.codigo} quedó {dato.estado} "
                    f"({segundos:.3f} s)\n      Inscripción oficial UUID: {inscripcion.codigo}"
                ))
            else:
                carro = servicios_carro.obtener_carro(estudiante)
                intacto = carro.items_activos.filter(curso=curso).exists()
                self.stdout.write(self.style.ERROR(
                    f"  ✗ {estudiante.username}: rechazado ({segundos:.3f} s) -> {dato.mensaje}"
                ))
                self.stdout.write(
                    f"      Su carro sigue intacto: {'sí' if intacto else 'no'} "
                    f"({carro.cantidad_cursos} curso(s) en el carro)"
                )

        curso.refresh_from_db()
        pagadas = sum(1 for r in resultados.values() if r[0] == "OK")
        self.stdout.write("")
        self.stdout.write(f"  Matrículas PAGADAS: {pagadas} · rechazadas: {len(resultados) - pagadas}")
        self.stdout.write(f"  Cupos disponibles finales: {curso.cupos_disponibles} (nunca -1)")
        if pagadas == 1 and curso.cupos_disponibles == 0:
            self.stdout.write(self.style.SUCCESS("Resultado correcto: el bloqueo de filas evitó la sobreventa del cupo."))
        else:
            self.stdout.write(self.style.ERROR("Resultado inesperado: revisa la configuración de la base de datos."))
