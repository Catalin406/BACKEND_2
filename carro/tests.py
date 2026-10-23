# ============================================================
# CARRO/TESTS.PY / PRUEBAS DEL CARRO DE MATRÍCULA PERSISTENTE
# Verifica: persistencia tras logout y nuevo login, duplicados (400
# sin filas repetidas), que agregar NO descuenta cupos, quitar y
# vaciar con baja lógica, y el panel HTML de carros.
# ============================================================
from rest_framework.test import APITestCase

from carro.models import CarroMatricula, ItemCarroMatricula
from core.fabricas import CLAVE, autenticar, crear_curso, crear_usuario
from cursos.models import Curso
from usuarios.models import Rol


class CarroApiTests(APITestCase):
    """GET/POST/DELETE /api/carro-matricula/."""

    def setUp(self):
        self.estudiante = crear_usuario("est")
        self.curso1 = crear_curso(cupos=5, costo=100000)
        self.curso2 = crear_curso(cupos=5, costo=250000)
        self.tokens = autenticar(self.client, self.estudiante)

    def test_carro_creado_por_senal(self):
        self.assertTrue(CarroMatricula.objects.filter(estudiante=self.estudiante).exists())

    def test_agregar_no_descuenta_cupos_y_calcula_total(self):
        self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        r = self.client.post("/api/carro-matricula/", {"curso": self.curso2.pk}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["cantidad_cursos"], 2)
        self.assertEqual(int(r.data["total"]), 350000)
        self.curso1.refresh_from_db()
        self.assertEqual(self.curso1.cupos_disponibles, 5)

    def test_duplicado_400_sin_filas_repetidas(self):
        self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        r = self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["mensaje"], "Este curso ya está en tu carro de matrícula.")
        self.assertEqual(ItemCarroMatricula.objects.filter(curso=self.curso1).count(), 1)

    def test_rechaza_curso_inactivo_y_sin_cupos(self):
        Curso.objects.filter(pk=self.curso1.pk).update(activo=False)
        Curso.objects.filter(pk=self.curso2.pk).update(cupos_disponibles=0)
        self.assertEqual(self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/carro-matricula/", {"curso": self.curso2.pk}, format="json").status_code, 400)

    def test_quitar_y_vaciar_son_baja_logica_y_reactivacion(self):
        self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        self.client.post("/api/carro-matricula/", {"curso": self.curso2.pk}, format="json")
        r = self.client.delete(f"/api/carro-matricula/items/{self.curso1.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(ItemCarroMatricula.objects.filter(curso=self.curso1, activo=False).exists())
        r = self.client.delete("/api/carro-matricula/")
        self.assertEqual(r.data["cantidad_cursos"], 0)
        self.assertEqual(ItemCarroMatricula.objects.count(), 2)
        # Volver a agregar reactiva la misma fila.
        self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        self.assertEqual(ItemCarroMatricula.objects.filter(curso=self.curso1).count(), 1)
        self.assertTrue(ItemCarroMatricula.objects.get(curso=self.curso1).activo)

    def test_carro_persiste_tras_logout_y_nuevo_login(self):
        self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        self.client.post("/api/carro-matricula/", {"curso": self.curso2.pk}, format="json")
        antes = self.client.get("/api/carro-matricula/").data["items"]
        r = self.client.post("/api/auth/logout/", {"refresh": self.tokens["refresh"]}, format="json")
        self.assertEqual(r.status_code, 200)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/carro-matricula/").status_code, 401)
        autenticar(self.client, self.estudiante)
        despues = self.client.get("/api/carro-matricula/").data["items"]
        self.assertEqual([i["curso"]["id"] for i in antes], [i["curso"]["id"] for i in despues])
        self.assertEqual(len(despues), 2)


class CarroHtmlTests(APITestCase):
    """Panel /panel/carros/."""

    def setUp(self):
        self.estudiante = crear_usuario("est")
        self.curso = crear_curso(cupos=2)
        crear_usuario("coord", rol=Rol.COORDINADOR)
        self.client.login(username="coord", password=CLAVE)

    def test_agregar_duplicado_muestra_error(self):
        url = f"/panel/carros/{self.estudiante.pk}/agregar/"
        self.client.post(url, {"curso": self.curso.pk})
        r = self.client.post(url, {"curso": self.curso.pk}, follow=True)
        self.assertContains(r, "Este curso ya está en tu carro de matrícula.")
        self.assertEqual(ItemCarroMatricula.objects.count(), 1)

    def test_vaciar_html(self):
        self.client.post(f"/panel/carros/{self.estudiante.pk}/agregar/", {"curso": self.curso.pk})
        self.client.post(f"/panel/carros/{self.estudiante.pk}/vaciar/")
        self.assertTrue(ItemCarroMatricula.objects.filter(activo=False).exists())
