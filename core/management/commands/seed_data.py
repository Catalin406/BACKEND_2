# ============================================================
# CORE/MANAGEMENT/COMMANDS/SEED_DATA.PY / DATOS DE PRUEBA
# python manage.py seed_data          -> carga idempotente
# python manage.py seed_data --reset  -> desactiva y recarga
# Crea 1 coordinador, 3 estudiantes, 6 áreas, 19 cursos (con cursos
# de 1 y 0 cupos), carros cargados y matrículas en cada estado con
# inscripciones e historial. Todo el escenario se construye con los
# mismos servicios que usa la API (carro y matrículas), por lo que
# los cupos quedan coherentes.
# ============================================================
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from carro import servicios as servicios_carro
from carro.models import ItemCarroMatricula
from cursos.models import AreaConocimiento, Curso, Modalidad, TipoCurso
from matriculas import servicios as servicios_matricula
from matriculas.models import DetalleMatricula, EstadoMatricula, HistorialEstadoMatricula, Inscripcion, Matricula
from usuarios.models import Rol, Usuario

# ============================================================
# DATOS BASE
# ============================================================
CLAVE_COORDINADOR = "Coordinador2026!"
CLAVE_ESTUDIANTE = "Estudiante2026!"

USUARIOS = [
    {"username": "coordinador", "first_name": "Andrea", "last_name": "Soto", "email": "coordinador@codelab.cl",
     "rol": Rol.COORDINADOR, "rut": "15.678.234-5", "telefono": "+56 9 8765 4321", "clave": CLAVE_COORDINADOR},
    {"username": "estudiante1", "first_name": "Valentina", "last_name": "Rojas", "email": "estudiante1@codelab.cl",
     "rol": Rol.ESTUDIANTE, "rut": "20.123.456-7", "telefono": "+56 9 1111 2222", "clave": CLAVE_ESTUDIANTE},
    {"username": "estudiante2", "first_name": "Matías", "last_name": "González", "email": "estudiante2@codelab.cl",
     "rol": Rol.ESTUDIANTE, "rut": "19.876.543-2", "telefono": "+56 9 3333 4444", "clave": CLAVE_ESTUDIANTE},
    {"username": "estudiante3", "first_name": "Fernanda", "last_name": "Muñoz", "email": "estudiante3@codelab.cl",
     "rol": Rol.ESTUDIANTE, "rut": "21.345.678-9", "telefono": "+56 9 5555 6666", "clave": CLAVE_ESTUDIANTE},
]

AREAS = [
    ("Desarrollo Web", "bi-code-slash", "Frontend, backend y desarrollo full stack con tecnologías actuales."),
    ("Ciencia de Datos", "bi-bar-chart-line", "Análisis, visualización y modelos estadísticos para tomar decisiones."),
    ("Ciberseguridad", "bi-shield-lock", "Seguridad ofensiva y defensiva, hacking ético y buenas prácticas."),
    ("Cloud y DevOps", "bi-cloud-arrow-up", "Contenedores, nube, automatización e integración continua."),
    ("Diseño UX/UI", "bi-palette", "Investigación de usuarios, prototipado e interfaces accesibles."),
    ("Inteligencia Artificial", "bi-cpu", "Machine learning, IA generativa y aplicaciones inteligentes."),
]

# (clave, título, área, tipo, modalidad, costo, inicio, término, cupos, descripción)
CURSOS = [
    ("fullstack", "Bootcamp Full Stack JavaScript", "Desarrollo Web", TipoCurso.BOOTCAMP, Modalidad.HIBRIDA,
     1490000, date(2026, 11, 2), date(2027, 2, 26), 25,
     "Programa intensivo de 16 semanas: HTML, CSS, JavaScript, React, Node.js, Express y MongoDB con proyecto final."),
    ("django", "Curso de Django y Django REST Framework", "Desarrollo Web", TipoCurso.CURSO, Modalidad.ONLINE,
     389990, date(2026, 10, 19), date(2026, 12, 18), 30,
     "Construye APIs REST profesionales con Django, autenticación JWT, filtros y documentación OpenAPI."),
    ("react", "Taller de React desde Cero", "Desarrollo Web", TipoCurso.TALLER, Modalidad.PRESENCIAL,
     89990, date(2026, 10, 24), date(2026, 10, 25), 15,
     "Dos jornadas prácticas para crear tu primera aplicación con componentes, estado y hooks."),
    ("git", "Taller de Git y GitHub", "Desarrollo Web", TipoCurso.TALLER, Modalidad.ONLINE,
     39990, date(2026, 10, 10), date(2026, 10, 10), 1,
     "Control de versiones, ramas, pull requests y flujo de trabajo colaborativo."),
    ("datascience", "Bootcamp de Ciencia de Datos con Python", "Ciencia de Datos", TipoCurso.BOOTCAMP,
     Modalidad.ONLINE, 1290000, date(2027, 1, 11), date(2027, 4, 30), 20,
     "Pandas, NumPy, visualización, estadística aplicada y modelos predictivos con casos reales."),
    ("sql", "Curso de SQL y PostgreSQL para Análisis", "Ciencia de Datos", TipoCurso.CURSO, Modalidad.ONLINE,
     249990, date(2026, 10, 13), date(2026, 11, 27), 35,
     "Consultas, joins, funciones de ventana e índices para análisis de datos en PostgreSQL."),
    ("powerbi", "Taller de Power BI", "Ciencia de Datos", TipoCurso.TALLER, Modalidad.HIBRIDA,
     69990, date(2026, 11, 14), date(2026, 11, 14), 20,
     "Crea tableros interactivos y reportes ejecutivos en una jornada."),
    ("python", "Taller de Introducción a Python", "Ciencia de Datos", TipoCurso.TALLER, Modalidad.ONLINE,
     29990, date(2026, 3, 7), date(2026, 3, 8), 30,
     "Primeros pasos en Python: variables, estructuras de control, funciones y archivos."),
    ("ciber", "Bootcamp de Ciberseguridad Ofensiva", "Ciberseguridad", TipoCurso.BOOTCAMP, Modalidad.PRESENCIAL,
     1590000, date(2026, 11, 16), date(2027, 3, 12), 2,
     "Hacking ético, pruebas de penetración, explotación de vulnerabilidades y reportes profesionales."),
    ("pentesting", "Taller de Pentesting con Kali Linux", "Ciberseguridad", TipoCurso.TALLER, Modalidad.PRESENCIAL,
     119990, date(2026, 12, 5), date(2026, 12, 6), 1,
     "Reconocimiento, escaneo y explotación en un laboratorio controlado."),
    ("owasp", "Curso de Seguridad en Aplicaciones Web (OWASP)", "Ciberseguridad", TipoCurso.CURSO,
     Modalidad.ONLINE, 299990, date(2027, 1, 18), date(2027, 3, 5), 25,
     "Las vulnerabilidades del OWASP Top 10 y cómo prevenirlas en tus aplicaciones."),
    ("docker", "Curso de Docker y Kubernetes", "Cloud y DevOps", TipoCurso.CURSO, Modalidad.ONLINE,
     349990, date(2026, 10, 20), date(2026, 12, 15), 25,
     "Contenedores, imágenes, orquestación con Kubernetes y despliegues reproducibles."),
    ("aws", "Bootcamp DevOps en AWS", "Cloud y DevOps", TipoCurso.BOOTCAMP, Modalidad.HIBRIDA,
     1390000, date(2027, 3, 1), date(2027, 6, 25), 20,
     "Infraestructura como código, pipelines, monitoreo y arquitectura en la nube de AWS."),
    ("cicd", "Taller de CI/CD con GitHub Actions", "Cloud y DevOps", TipoCurso.TALLER, Modalidad.ONLINE,
     79990, date(2026, 11, 21), date(2026, 11, 21), 30,
     "Automatiza pruebas y despliegues con flujos de GitHub Actions."),
    ("figma", "Curso de Diseño UX/UI con Figma", "Diseño UX/UI", TipoCurso.CURSO, Modalidad.HIBRIDA,
     279990, date(2026, 10, 26), date(2026, 12, 11), 20,
     "Investigación de usuarios, arquitectura de información, wireframes y prototipos en Figma."),
    ("prototipado", "Taller de Prototipado Rápido", "Diseño UX/UI", TipoCurso.TALLER, Modalidad.PRESENCIAL,
     59990, date(2026, 11, 7), date(2026, 11, 7), 12,
     "Técnicas para validar ideas en horas: bocetos, prototipos en papel y pruebas con usuarios."),
    ("ia", "Bootcamp de Inteligencia Artificial Aplicada", "Inteligencia Artificial", TipoCurso.BOOTCAMP,
     Modalidad.ONLINE, 1690000, date(2027, 4, 5), date(2027, 8, 27), 20,
     "Redes neuronales, IA generativa, modelos de lenguaje e integración de IA en productos."),
    ("ml", "Curso de Machine Learning con scikit-learn", "Inteligencia Artificial", TipoCurso.CURSO,
     Modalidad.ONLINE, 329990, date(2027, 1, 25), date(2027, 3, 26), 25,
     "Regresión, clasificación, clustering y evaluación de modelos con scikit-learn."),
    ("prompt", "Taller de Prompt Engineering", "Inteligencia Artificial", TipoCurso.TALLER, Modalidad.ONLINE,
     49990, date(2026, 10, 17), date(2026, 10, 17), 40,
     "Diseña instrucciones efectivas para modelos de lenguaje y automatiza tareas cotidianas."),
]


class Command(BaseCommand):
    """Carga (o recarga con --reset) los datos de demostración."""

    help = "Carga datos de prueba idempotentes. Con --reset desactiva lo existente y recarga el escenario."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Desactiva los datos actuales y recarga el escenario.")

    # ============================================================
    # FLUJO PRINCIPAL
    # ============================================================
    def handle(self, *args, **opciones):
        reset = opciones["reset"]
        if reset:
            self._reiniciar()
        usuarios = self._cargar_usuarios()
        areas = self._cargar_areas()
        cursos = self._cargar_cursos(areas)
        estudiantes = [usuarios[f"estudiante{i}"] for i in (1, 2, 3)]
        if reset or not Matricula.objects.filter(estudiante__in=estudiantes).exists():
            self._cargar_escenario(usuarios, cursos)
        else:
            self.stdout.write("  · Escenario de carros y matrículas ya existente: no se duplica.")
        self._resumen()

    # ============================================================
    # RESET: DESACTIVA SIN BORRAR FILAS
    # Cancela matrículas abiertas (liberando cupos con el servicio),
    # inactiva inscripciones de matrículas completadas, vacía carros y
    # desactiva áreas y cursos. Luego la carga los reactiva.
    # ============================================================
    def _reiniciar(self):
        self.stdout.write(self.style.WARNING("Reiniciando datos (baja lógica, sin borrar filas)..."))
        coordinador = Usuario.objects.filter(username="coordinador").first()
        for matricula in Matricula.objects.filter(estado__in=[EstadoMatricula.PENDIENTE, EstadoMatricula.PAGADO]):
            servicios_matricula.cambiar_estado_matricula(
                matricula, EstadoMatricula.CANCELADO, coordinador, "Reinicio de datos de prueba (seed_data --reset)."
            )
        with transaction.atomic():
            activas = Inscripcion.objects.filter(activa=True).select_related("detalle")
            for inscripcion in activas:
                Curso.objects.filter(pk=inscripcion.detalle.curso_id).update(
                    cupos_disponibles=F("cupos_disponibles") + 1
                )
            activas.update(activa=False)
        ItemCarroMatricula.objects.filter(activo=True).update(activo=False)
        Curso.objects.update(activo=False)
        AreaConocimiento.objects.update(activo=False)

    # ============================================================
    # USUARIOS
    # ============================================================
    def _cargar_usuarios(self):
        usuarios = {}
        for datos in USUARIOS:
            datos = dict(datos)
            clave = datos.pop("clave")
            usuario, creado = Usuario.objects.get_or_create(username=datos["username"], defaults=datos)
            if creado:
                usuario.set_password(clave)
            else:
                for campo, valor in datos.items():
                    setattr(usuario, campo, valor)
            usuario.is_active = True
            usuario.save()
            usuarios[usuario.username] = usuario
        self.stdout.write(self.style.SUCCESS(f"  ✓ Usuarios: {len(usuarios)} (1 coordinador, 3 estudiantes)"))
        return usuarios

    # ============================================================
    # ÁREAS
    # ============================================================
    def _cargar_areas(self):
        areas = {}
        for nombre, icono, descripcion in AREAS:
            area, _ = AreaConocimiento.objects.update_or_create(
                nombre=nombre, defaults={"icono": icono, "descripcion": descripcion, "activo": True}
            )
            areas[nombre] = area
        self.stdout.write(self.style.SUCCESS(f"  ✓ Áreas de conocimiento: {len(areas)}"))
        return areas

    # ============================================================
    # CURSOS (una cohorte por título + fecha de inicio)
    # ============================================================
    def _cargar_cursos(self, areas):
        cursos = {}
        for clave, titulo, area, tipo, modalidad, costo, inicio, termino, cupos, descripcion in CURSOS:
            curso = Curso.objects.filter(titulo=titulo, fecha_inicio=inicio).first() or Curso(
                titulo=titulo, fecha_inicio=inicio
            )
            curso.area = areas[area]
            curso.tipo = tipo
            curso.modalidad = modalidad
            curso.costo_matricula = Decimal(costo)
            curso.fecha_termino = termino
            curso.descripcion = descripcion
            curso.activo = True
            if curso.pk is None or curso.cupos_ocupados_en_bd() <= cupos:
                curso.cupos_maximos = cupos
            curso.save()
            cursos[clave] = curso
        self.stdout.write(self.style.SUCCESS(f"  ✓ Cursos, bootcamps y talleres: {len(cursos)}"))
        return cursos

    # ============================================================
    # ESCENARIO: CARROS Y MATRÍCULAS EN CADA ESTADO
    # ============================================================
    def _cargar_escenario(self, usuarios, cursos):
        coordinador = usuarios["coordinador"]
        e1, e2, e3 = usuarios["estudiante1"], usuarios["estudiante2"], usuarios["estudiante3"]
        for estudiante in (e1, e2, e3):
            servicios_carro.vaciar_carro(estudiante)

        def matricular(estudiante, claves):
            for clave in claves:
                servicios_carro.agregar_curso(estudiante, cursos[clave])
            return servicios_matricula.confirmar_matricula(estudiante)

        # Estudiante 1: matrícula PAGADA y carro con el bootcamp que luego se agota.
        matricular(e1, ["django"])
        for clave in ("ciber", "figma", "datascience"):
            servicios_carro.agregar_curso(e1, cursos[clave])

        # Estudiante 2: matrícula PAGADA (toma 1 de los 2 cupos del bootcamp de ciberseguridad).
        matricular(e2, ["ciber", "sql"])

        # Estudiante 3: COMPLETADA, PAGADA (último cupo de ciberseguridad) y CANCELADA (libera cupo).
        completada = matricular(e3, ["python"])
        servicios_matricula.cambiar_estado_matricula(
            completada, EstadoMatricula.COMPLETADO, coordinador, "Taller finalizado con asistencia completa."
        )
        matricular(e3, ["ciber", "docker"])
        cancelada = matricular(e3, ["cicd"])
        servicios_matricula.cambiar_estado_matricula(
            cancelada, EstadoMatricula.CANCELADO, coordinador, "El estudiante solicitó la anulación."
        )

        # Estudiante 2: matrícula PENDIENTE (pago aún no aprobado: no descuenta cupos ni emite inscripciones).
        # Es la que se usa para demostrar el pago con Webpay: el Coordinador entra a su detalle en el
        # panel y presiona "Pagar con Webpay" (el curso de ML tiene 25 cupos, así que el pago se aprueba).
        with transaction.atomic():
            pendiente = Matricula.objects.create(estudiante=e2)
            DetalleMatricula.objects.create(
                matricula=pendiente, curso=cursos["ml"], costo_matricula=cursos["ml"].costo_matricula
            )
            HistorialEstadoMatricula.objects.create(
                matricula=pendiente, estado_anterior=None, estado_nuevo=EstadoMatricula.PENDIENTE,
                cambiado_por=e2, observacion="Matrícula creada; pago en espera de aprobación.",
            )

        # Carros cargados para la demostración.
        servicios_carro.agregar_curso(e2, cursos["pentesting"])
        servicios_carro.agregar_curso(e2, cursos["powerbi"])
        servicios_carro.agregar_curso(e3, cursos["prompt"])
        servicios_carro.agregar_curso(e3, cursos["react"])
        self.stdout.write(self.style.SUCCESS("  ✓ Escenario: carros cargados y matrículas en los 4 estados"))

    # ============================================================
    # RESUMEN EN CONSOLA
    # ============================================================
    def _resumen(self):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Resumen de datos de prueba"))
        for valor, etiqueta in EstadoMatricula.choices:
            self.stdout.write(f"  Matrículas en estado {etiqueta}: {Matricula.objects.filter(estado=valor).count()}")
        self.stdout.write(f"  Inscripciones activas: {Inscripcion.objects.filter(activa=True).count()}")
        agotados = Curso.objects.filter(activo=True, cupos_disponibles=0).values_list("titulo", flat=True)
        un_cupo = Curso.objects.filter(activo=True, cupos_disponibles=1).values_list("titulo", flat=True)
        self.stdout.write(f"  Cursos sin cupos: {', '.join(agotados) or '—'}")
        self.stdout.write(f"  Cursos con 1 cupo: {', '.join(un_cupo) or '—'}")
        self.stdout.write("")
        self.stdout.write(f"  Coordinador: coordinador / {CLAVE_COORDINADOR}")
        self.stdout.write(f"  Estudiantes: estudiante1, estudiante2, estudiante3 / {CLAVE_ESTUDIANTE}")
        self.stdout.write(self.style.SUCCESS("Datos de prueba listos."))
