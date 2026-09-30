# ============================================================
# MATRICULAS/TESTS.PY / PRUEBAS DE CONFIRMACIÓN, CUPOS Y ESTADOS
# Verifica: confirmar descuenta 1 cupo por curso, congela el costo y
# emite UUID distintos; sin cupo -> 409 con rollback total;
# cancelar libera cupos e inactiva inscripciones; transiciones
# inválidas -> 400; aislamiento de "mis matrículas"; y concurrencia
# real con dos hilos (TransactionTestCase).
# ============================================================
import threading

from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APITestCase

from carro import servicios as servicios_carro
from carro.models import ItemCarroMatricula
from core.excepciones import ErrorDeNegocio
from core.fabricas import autenticar, crear_curso, crear_usuario
from cursos.models import Curso
from matriculas import servicios
from matriculas.models import EstadoMatricula, HistorialEstadoMatricula, Inscripcion, Matricula
from usuarios.models import Rol


class ConfirmacionTests(APITestCase):
    """POST /api/matriculas/confirmar/."""

    def setUp(self):
        self.estudiante = crear_usuario("est")
        self.curso1 = crear_curso(cupos=3, costo=120000)
        self.curso2 = crear_curso(cupos=1, costo=80000)
        autenticar(self.client, self.estudiante)
        self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        self.client.post("/api/carro-matricula/", {"curso": self.curso2.pk}, format="json")

    def test_confirmar_descuenta_congela_costo_y_emite_uuid(self):
        r = self.client.post("/api/matriculas/confirmar/")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["estado"], "PAGADO")
        self.assertEqual(int(r.data["total"]), 200000)
        self.curso1.refresh_from_db()
        self.curso2.refresh_from_db()
        self.assertEqual(self.curso1.cupos_disponibles, 2)
        self.assertEqual(self.curso2.cupos_disponibles, 0)
        codigos = [d["inscripcion"]["codigo"] for d in r.data["detalles"]]
        self.assertEqual(len(codigos), 2)
        self.assertEqual(len(set(codigos)), 2)
        # Costo congelado: cambiar el precio del curso no altera la matrícula.
        Curso.objects.filter(pk=self.curso1.pk).update(costo_matricula=999999)
        matricula = Matricula.objects.get(pk=r.data["id"])
        self.assertEqual(int(matricula.total), 200000)
        # Historial None -> PENDIENTE -> PAGADO y carro vacío.
        estados = list(matricula.historial.values_list("estado_anterior", "estado_nuevo"))
        self.assertEqual(estados, [(None, "PENDIENTE"), ("PENDIENTE", "PAGADO")])
        self.assertEqual(self.client.get("/api/carro-matricula/").data["cantidad_cursos"], 0)

    def test_sin_cupo_409_rollback_total(self):
        Curso.objects.filter(pk=self.curso2.pk).update(cupos_disponibles=0)
        r = self.client.post("/api/matriculas/confirmar/")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["detalle"]["cursos_sin_cupo"][0]["curso_id"], self.curso2.pk)
        self.assertFalse(Matricula.objects.exists())
        self.curso1.refresh_from_db()
        self.assertEqual(self.curso1.cupos_disponibles, 3)
        self.assertEqual(ItemCarroMatricula.objects.filter(activo=True).count(), 2)

    def test_carro_vacio_400(self):
        self.client.delete("/api/carro-matricula/")
        self.assertEqual(self.client.post("/api/matriculas/confirmar/").status_code, 400)

    def test_no_permite_curso_ya_inscrito(self):
        self.client.post("/api/matriculas/confirmar/")
        r = self.client.post("/api/carro-matricula/", {"curso": self.curso1.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_mis_matriculas_solo_propias(self):
        self.client.post("/api/matriculas/confirmar/")
        otro = crear_usuario("otro")
        ajena = Matricula.objects.create(estudiante=otro)
        r = self.client.get("/api/mis-matriculas/")
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(self.client.get(f"/api/mis-matriculas/{ajena.pk}/").status_code, 404)


class CambioEstadoTests(APITestCase):
    """PATCH /api/matriculas/{id}/estado/."""

    def setUp(self):
        self.estudiante = crear_usuario("est")
        self.coordinador = crear_usuario("coord", rol=Rol.COORDINADOR)
        self.curso = crear_curso(cupos=2)
        servicios_carro.agregar_curso(self.estudiante, self.curso)
        self.matricula = servicios.confirmar_matricula(self.estudiante)
        autenticar(self.client, self.coordinador)

    def _patch(self, estado):
        return self.client.patch(f"/api/matriculas/{self.matricula.pk}/estado/", {"estado": estado}, format="json")

    def test_cancelar_pagada_libera_cupos_e_inactiva_inscripciones(self):
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.cupos_disponibles, 1)
        r = self._patch("CANCELADO")
        self.assertEqual(r.status_code, 200)
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.cupos_disponibles, 2)
        self.assertFalse(Inscripcion.objects.filter(activa=True).exists())
        self.assertTrue(HistorialEstadoMatricula.objects.filter(
            matricula=self.matricula, estado_anterior="PAGADO", estado_nuevo="CANCELADO", cambiado_por=self.coordinador
        ).exists())

    def test_transiciones_invalidas_400(self):
        self.assertEqual(self._patch("PENDIENTE").status_code, 400)
        self.assertEqual(self._patch("COMPLETADO").status_code, 200)
        r = self._patch("CANCELADO")
        self.assertEqual(r.status_code, 400)
        self.assertIn("estado final", r.data["mensaje"])
        self.assertEqual(self._patch("INVENTADO").status_code, 400)
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.cupos_disponibles, 1)

    def test_filtro_matriculas_coordinador(self):
        r = self.client.get(f"/api/matriculas/?estado=PAGADO&curso={self.curso.pk}")
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(self.client.get("/api/matriculas/?estado=CANCELADO").data["count"], 0)
        r = self.client.get(f"/api/inscripciones/?curso={self.curso.pk}&activa=true")
        self.assertEqual(r.data["count"], 1)

    def test_cancelar_desde_html(self):
        r = self.client.post(f"/panel/matriculas/{self.matricula.pk}/estado/", {"estado": "CANCELADO"}, follow=True)
        self.assertContains(r, "Los cupos de sus cursos fueron liberados")
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.cupos_disponibles, 2)


class ConfirmacionHtmlTests(APITestCase):
    """Confirmar desde /panel/carros/ muestra qué curso quedó sin cupo."""

    def test_sin_cupo_html_muestra_mensaje(self):
        estudiante = crear_usuario("est")
        curso = crear_curso(titulo="Taller Agotado", cupos=1)
        servicios_carro.agregar_curso(estudiante, curso)
        Curso.objects.filter(pk=curso.pk).update(cupos_disponibles=0)
        r = self.client.post(f"/panel/carros/{estudiante.pk}/confirmar/", follow=True)
        self.assertContains(r, "No hay cupos disponibles en: «Taller Agotado»")
        self.assertFalse(Matricula.objects.exists())


class ConcurrenciaTests(TransactionTestCase):
    """Dos confirmaciones simultáneas por el último cupo."""

    def test_solo_una_matricula_queda_pagada(self):
        curso = crear_curso(cupos=1)
        estudiantes = [crear_usuario("hilo_a"), crear_usuario("hilo_b")]
        for estudiante in estudiantes:
            servicios_carro.agregar_curso(estudiante, curso)
        barrera = threading.Barrier(2)
        resultados = []

        def confirmar(estudiante):
            try:
                barrera.wait()
                servicios.confirmar_matricula(estudiante)
                resultados.append("OK")
            except ErrorDeNegocio as error:
                resultados.append(type(error).__name__)
            finally:
                connection.close()

        hilos = [threading.Thread(target=confirmar, args=(e,)) for e in estudiantes]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(sorted(resultados), ["OK", "SinCuposError"])
        curso.refresh_from_db()
        self.assertEqual(curso.cupos_disponibles, 0)
        self.assertEqual(Matricula.objects.filter(estado=EstadoMatricula.PAGADO).count(), 1)
        self.assertEqual(ItemCarroMatricula.objects.filter(activo=True).count(), 1)
