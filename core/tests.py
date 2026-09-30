# ============================================================
# CORE/TESTS.PY / PRUEBAS DE RUTAS, FOOTER Y FORMATO
# Verifica: ninguna ruta inexistente devuelve 404 (terminan en la
# pantalla de redirección), /cursos redirige a /cursos/, la API
# responde JSON controlado, y todas las páginas HTML principales
# muestran el nombre, la sección y el año de la alumna.
# ============================================================
from django.conf import settings
from django.test import TestCase

from carro import servicios as servicios_carro
from core.fabricas import crear_curso, crear_usuario
from core.templatetags.formato import clp
from matriculas import servicios as servicios_matricula

RUTAS_INEXISTENTES = [
    "/asdf", "/api/xyz", "/panel/cursos/999999/", "/cursos/abc/", "/%%%",
    "/panel/areas/999999/editar/", "/panel/usuarios/0/", "/panel/matriculas/999999/",
    "/cursos/999999/", "/x/y/z/", "/panel/carros/?estudiante=abc",
]


class RutasInexistentesTests(TestCase):
    """El 404 de Django no debe aparecer nunca."""

    def test_rutas_absurdas_llevan_a_la_redireccion(self):
        for ruta in RUTAS_INEXISTENTES:
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta, follow=True)
                self.assertNotEqual(r.status_code, 404)
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, "La página que buscas no existe")
                self.assertContains(r, 'http-equiv="refresh" content="3;url=/"')

    def test_ruta_sin_barra_redirige_a_con_barra(self):
        r = self.client.get("/cursos")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r["Location"], "/cursos/")
        r = self.client.get("/panel/areas?q=web")
        self.assertEqual(r["Location"], "/panel/areas/?q=web")

    def test_raiz_carga_inicio(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "core/inicio.html")

    def test_api_recurso_inexistente_json_controlado(self):
        r = self.client.get("/api/cursos/999999/")
        self.assertEqual(r["Content-Type"], "application/json")
        self.assertEqual(r.json()["redireccion"], "/")
        self.assertTrue(r.json()["error"])


class FooterEnTodasLasPaginasTests(TestCase):
    """Nombre, sección y año visibles en cada pantalla."""

    def setUp(self):
        self.estudiante = crear_usuario("est")
        self.curso = crear_curso()
        servicios_carro.agregar_curso(self.estudiante, self.curso)
        self.matricula = servicios_matricula.confirmar_matricula(self.estudiante)

    def test_paginas_principales_200_con_datos_alumna(self):
        area = self.curso.area_id
        rutas = [
            "/", "/cursos/", f"/cursos/{self.curso.pk}/", "/panel/", "/documentacion/",
            "/panel/areas/", "/panel/areas/nueva/", f"/panel/areas/{area}/", f"/panel/areas/{area}/editar/",
            f"/panel/areas/{area}/desactivar/", "/panel/cursos/", "/panel/cursos/nuevo/",
            f"/panel/cursos/{self.curso.pk}/", f"/panel/cursos/{self.curso.pk}/editar/",
            "/panel/usuarios/", "/panel/usuarios/nuevo/", f"/panel/usuarios/{self.estudiante.pk}/",
            "/panel/carros/", f"/panel/carros/?estudiante={self.estudiante.pk}", "/panel/matriculas/",
            f"/panel/matriculas/{self.matricula.pk}/", "/panel/inscripciones/", "/asdf",
            "/api/docs/", "/api/redoc/",
        ]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                r = self.client.get(ruta)
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, settings.ALUMNO_NOMBRE)
                self.assertContains(r, f"Sección {settings.ALUMNO_SECCION}")
                self.assertContains(r, settings.ALUMNO_ANIO)
                self.assertContains(r, "/documentacion/")

    def test_browsable_api_con_footer(self):
        r = self.client.get("/api/cursos/", HTTP_ACCEPT="text/html")
        self.assertContains(r, settings.ALUMNO_NOMBRE)

    def test_raiz_api_datos_alumna(self):
        datos = self.client.get("/api/", HTTP_ACCEPT="application/json").json()
        self.assertEqual(datos["alumna"]["seccion"], settings.ALUMNO_SECCION)


class FormatoTests(TestCase):
    """Filtro |clp."""

    def test_clp(self):
        self.assertEqual(clp(349990), "$349.990")
        self.assertEqual(clp(1490000), "$1.490.000")
        self.assertEqual(clp(None), "$0")
