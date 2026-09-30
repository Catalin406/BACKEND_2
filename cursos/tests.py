# ============================================================
# CURSOS/TESTS.PY / PRUEBAS DE CURSOS, ÁREAS Y FILTROS
# Verifica los filtros de CursoFilter (area, tipo, costo_min,
# costo_max, inicio_desde, con_cupos), las validaciones del curso,
# el ajuste de cupos al editar el máximo y la baja lógica (API y HTML).
# ============================================================
from datetime import date

from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from core.fabricas import autenticar, crear_area, crear_curso, crear_usuario
from cursos.models import AreaConocimiento, Curso, TipoCurso
from usuarios.models import Rol


class FiltrosCursoTests(APITestCase):
    """Filtros de /api/cursos/."""

    def setUp(self):
        self.web = crear_area("Web")
        self.datos = crear_area("Datos")
        self.barato = crear_curso(self.web, "Taller barato", costo=30000, tipo=TipoCurso.TALLER,
                                  fecha_inicio=date(2026, 11, 1), fecha_termino=date(2026, 11, 2))
        self.medio = crear_curso(self.datos, "Curso medio", costo=300000,
                                 fecha_inicio=date(2027, 1, 5), fecha_termino=date(2027, 2, 5))
        self.caro = crear_curso(self.web, "Bootcamp caro", costo=1500000, tipo=TipoCurso.BOOTCAMP, cupos=1,
                                fecha_inicio=date(2027, 3, 1), fecha_termino=date(2027, 6, 1))
        Curso.objects.filter(pk=self.caro.pk).update(cupos_disponibles=0)

    def _titulos(self, query):
        r = self.client.get(f"/api/cursos/?{query}")
        self.assertEqual(r.status_code, 200)
        return {c["titulo"] for c in r.data["results"]}

    def test_filtro_area(self):
        self.assertEqual(self._titulos(f"area={self.web.pk}"), {"Taller barato", "Bootcamp caro"})

    def test_filtro_tipo(self):
        self.assertEqual(self._titulos("tipo=BOOTCAMP"), {"Bootcamp caro"})

    def test_filtro_costo_min_y_max(self):
        self.assertEqual(self._titulos("costo_min=100000"), {"Curso medio", "Bootcamp caro"})
        self.assertEqual(self._titulos("costo_max=300000"), {"Taller barato", "Curso medio"})
        self.assertEqual(self._titulos("costo_min=100000&costo_max=400000"), {"Curso medio"})

    def test_filtro_inicio_desde(self):
        self.assertEqual(self._titulos("inicio_desde=2027-01-01"), {"Curso medio", "Bootcamp caro"})

    def test_filtro_con_cupos(self):
        self.assertEqual(self._titulos("con_cupos=true"), {"Taller barato", "Curso medio"})
        self.assertEqual(self._titulos("con_cupos=false"), {"Bootcamp caro"})

    def test_busqueda_y_orden(self):
        self.assertEqual(self._titulos("search=datos"), {"Curso medio"})
        r = self.client.get("/api/cursos/?ordering=-costo_matricula")
        self.assertEqual(r.data["results"][0]["titulo"], "Bootcamp caro")

    def test_lectura_muestra_area_anidada_y_duracion(self):
        r = self.client.get(f"/api/cursos/{self.barato.pk}/")
        self.assertEqual(r.data["area"]["nombre"], "Web")
        self.assertEqual(r.data["duracion_dias"], 2)
        self.assertEqual(r.data["tipo_display"], "Taller")

    def test_filtros_en_vista_html(self):
        r = self.client.get(f"/cursos/?tipo=BOOTCAMP&area={self.web.pk}")
        self.assertContains(r, "Bootcamp caro")
        self.assertNotContains(r, "Taller barato")


class ValidacionesCursoTests(APITestCase):
    """Reglas de negocio del curso."""

    def setUp(self):
        self.coordinador = crear_usuario("coord", rol=Rol.COORDINADOR)
        self.area = crear_area()
        autenticar(self.client, self.coordinador)

    def test_fechas_incoherentes_400(self):
        r = self.client.post("/api/cursos/", {
            "titulo": "X", "descripcion": "d", "area": self.area.pk, "tipo": "CURSO", "modalidad": "ONLINE",
            "costo_matricula": 1000, "fecha_inicio": "2027-02-01", "fecha_termino": "2027-01-01", "cupos_maximos": 3,
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("fecha_termino", r.data["detalle"])

    def test_cohorte_duplicada_400(self):
        curso = crear_curso(self.area, "Repetido")
        r = self.client.post("/api/cursos/", {
            "titulo": "Repetido", "descripcion": "d", "area": self.area.pk, "tipo": "CURSO", "modalidad": "ONLINE",
            "costo_matricula": 1000, "fecha_inicio": curso.fecha_inicio.isoformat(),
            "fecha_termino": curso.fecha_termino.isoformat(), "cupos_maximos": 3,
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_ajuste_de_cupos_al_cambiar_maximo(self):
        curso = crear_curso(self.area, cupos=10)
        Curso.objects.filter(pk=curso.pk).update(cupos_disponibles=7)  # 3 ocupados
        curso.refresh_from_db()
        curso.cupos_maximos = 12
        curso.save()
        self.assertEqual(curso.cupos_disponibles, 9)
        curso.cupos_maximos = 2
        with self.assertRaises(ValidationError):
            curso.save()

    def test_area_delete_y_reactivar_api(self):
        r = self.client.delete(f"/api/areas/{self.area.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(AreaConocimiento.objects.filter(pk=self.area.pk, activo=False).exists())
        self.client.credentials()
        self.assertEqual(self.client.get(f"/api/areas/{self.area.pk}/").status_code, 404)
        autenticar(self.client, self.coordinador)
        self.assertEqual(self.client.post(f"/api/areas/{self.area.pk}/reactivar/").status_code, 200)

    def test_inactivos_solo_para_coordinador(self):
        curso = crear_curso(self.area)
        Curso.objects.filter(pk=curso.pk).update(activo=False)
        r = self.client.get("/api/cursos/?incluir_inactivos=true")
        self.assertEqual(r.data["count"], 1)
        self.client.credentials()
        r = self.client.get("/api/cursos/?incluir_inactivos=true")
        self.assertEqual(r.data["count"], 0)


class CursosHtmlTests(APITestCase):
    """CRUD HTML de áreas y cursos con baja lógica."""

    def test_crear_curso_html_y_desactivar_sin_borrar(self):
        area = crear_area()
        r = self.client.post("/panel/cursos/nuevo/", {
            "titulo": "Curso HTML", "descripcion": "d", "area": area.pk, "tipo": "CURSO", "modalidad": "HIBRIDA",
            "costo_matricula": 99990, "fecha_inicio": "2027-01-01", "fecha_termino": "2027-01-31", "cupos_maximos": 4,
        })
        self.assertEqual(r.status_code, 302)
        curso = Curso.objects.get(titulo="Curso HTML")
        self.assertEqual(curso.cupos_disponibles, 4)
        self.client.post(f"/panel/cursos/{curso.pk}/desactivar/")
        self.assertTrue(Curso.objects.filter(pk=curso.pk, activo=False).exists())
        self.client.post(f"/panel/areas/{area.pk}/desactivar/")
        self.assertTrue(AreaConocimiento.objects.filter(pk=area.pk, activo=False).exists())

    def test_formulario_html_muestra_errores(self):
        area = crear_area()
        r = self.client.post("/panel/cursos/nuevo/", {
            "titulo": "Malo", "descripcion": "d", "area": area.pk, "tipo": "CURSO", "modalidad": "ONLINE",
            "costo_matricula": 0, "fecha_inicio": "2027-02-01", "fecha_termino": "2027-01-01", "cupos_maximos": 1,
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "La fecha de término no puede ser anterior")
        self.assertContains(r, "mayor a 0")
