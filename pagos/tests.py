# ============================================================
# PAGOS/TESTS.PY / PRUEBAS DEL PAGO CON WEBPAY PLUS (SIN LLAMAR A TRANSBANK)
# Todo Transbank se reemplaza con unittest.mock: pagos.servicios._transaccion
# devuelve un falso con create/commit/refund. Se comprueba que:
#  - aprobado descuenta cupos y crea inscripciones; rechazado no;
#  - anulado y timeout cierran el pago sin cobro;
#  - el retorno es idempotente (un token no se procesa dos veces);
#  - monto distinto o falta de cupos -> refund y matrícula PENDIENTE;
#  - dos pagos aprobados de la misma matrícula: el segundo se reembolsa;
#  - un estudiante no puede pagar una matrícula ajena (403);
#  - confirmar_matricula (pago simulado) sigue igual que antes.
# ============================================================
from unittest import mock

from django.test import Client
from rest_framework.test import APITestCase
from transbank.error.transbank_error import TransbankError

from carro import servicios as servicios_carro
from core.fabricas import CLAVE, autenticar, crear_curso, crear_usuario
from cursos.models import Curso
from matriculas import servicios as servicios_matricula
from matriculas.models import EstadoMatricula, Inscripcion, Matricula
from pagos import servicios
from pagos.models import EstadoPago, PagoWebpay
from usuarios.models import Rol

URL_WEBPAY = "https://webpay3gint.transbank.cl/webpayserver/initTransaction"
RETORNO = "http://testserver/pagos/webpay/retorno/"


def respuesta_commit(pago, aprobado=True, monto=None):
    """Respuesta de Transbank al commit, con la forma real del SDK."""
    return {
        "vci": "TSY", "amount": pago.monto if monto is None else monto,
        "status": "AUTHORIZED" if aprobado else "FAILED", "buy_order": pago.buy_order,
        "session_id": pago.session_id, "card_detail": {"card_number": "6623"},
        "accounting_date": "1023", "transaction_date": "2026-10-23T12:00:00.000Z",
        "authorization_code": "1213" if aprobado else "000000", "payment_type_code": "VN",
        "response_code": 0 if aprobado else -1, "installments_number": 0,
    }


class BasePagosTests(APITestCase):
    """Prepara un estudiante con un curso en el carro y un Transbank falso."""

    def setUp(self):
        parche = mock.patch("pagos.servicios._transaccion")
        self.tx = parche.start().return_value
        self.addCleanup(parche.stop)
        self.tx.create.side_effect = lambda buy_order, session_id, amount, return_url: {
            "token": f"tk-{buy_order}", "url": URL_WEBPAY,
        }
        self.tx.refund.return_value = {"type": "REVERSED", "response_code": 0}
        self.estudiante = crear_usuario("est")
        self.coordinador = crear_usuario("coord", rol=Rol.COORDINADOR)
        self.curso = crear_curso(cupos=3, costo=120000)

    def matricula_pendiente(self, estudiante=None, curso=None):
        estudiante = estudiante or self.estudiante
        servicios_carro.agregar_curso(estudiante, curso or self.curso)
        return servicios_matricula.crear_matricula_pendiente(estudiante)

    def iniciar(self, matricula):
        pago, _url = servicios.iniciar_pago_webpay(matricula, RETORNO)
        return pago

    def aprobar_en_transbank(self, *pagos, **kwargs):
        """El commit responde, en orden, aprobado para cada pago dado."""
        self.tx.commit.side_effect = [respuesta_commit(p, **kwargs) for p in pagos]

    def cupos(self, curso=None):
        c = curso or self.curso
        return Curso.objects.get(pk=c.pk).cupos_disponibles


class PagoAprobadoYRechazadoTests(BasePagosTests):
    def test_iniciar_crea_pago_iniciado_con_monto_del_servidor(self):
        matricula = self.matricula_pendiente()
        pago, url = servicios.iniciar_pago_webpay(matricula, RETORNO)
        self.assertEqual(url, URL_WEBPAY)
        self.assertEqual(pago.estado, EstadoPago.INICIADO)
        self.assertEqual(pago.monto, 120000)
        self.assertLessEqual(len(pago.buy_order), 26)
        self.tx.create.assert_called_once_with(pago.buy_order, pago.session_id, 120000, RETORNO)

    def test_aprobado_descuenta_cupos_y_crea_inscripciones(self):
        matricula = self.matricula_pendiente()
        pago = self.iniciar(matricula)
        self.aprobar_en_transbank(pago)
        resultado = servicios.confirmar_pago_webpay(pago.token)
        self.assertEqual(resultado.estado, EstadoPago.APROBADO)
        self.assertEqual((resultado.authorization_code, resultado.card_number), ("1213", "6623"))
        matricula.refresh_from_db()
        self.assertEqual(matricula.estado, EstadoMatricula.PAGADO)
        self.assertEqual(self.cupos(), 2)
        self.assertEqual(Inscripcion.objects.filter(detalle__matricula=matricula, activa=True).count(), 1)
        self.assertEqual(servicios_carro.obtener_carro(self.estudiante).items.filter(activo=True).count(), 0)

    def test_rechazado_no_descuenta(self):
        matricula = self.matricula_pendiente()
        pago = self.iniciar(matricula)
        self.aprobar_en_transbank(pago, aprobado=False)
        resultado = servicios.confirmar_pago_webpay(pago.token)
        self.assertEqual(resultado.estado, EstadoPago.RECHAZADO)
        matricula.refresh_from_db()
        self.assertEqual(matricula.estado, EstadoMatricula.PENDIENTE)
        self.assertEqual(self.cupos(), 3)
        self.assertFalse(Inscripcion.objects.exists())
        self.tx.refund.assert_not_called()

    def test_error_de_transbank_en_commit_deja_pago_en_error(self):
        pago = self.iniciar(self.matricula_pendiente())
        self.tx.commit.side_effect = TransbankError("fallo", 422)
        self.assertEqual(servicios.confirmar_pago_webpay(pago.token).estado, EstadoPago.ERROR)
        self.assertEqual(self.cupos(), 3)


class AnulacionTimeoutYFormularioTests(BasePagosTests):
    def test_anulacion_por_el_usuario(self):
        pago = self.iniciar(self.matricula_pendiente())
        resultado = servicios.procesar_retorno(
            {"TBK_TOKEN": pago.token, "TBK_ORDEN_COMPRA": pago.buy_order, "TBK_ID_SESION": pago.session_id}
        )
        self.assertEqual(resultado.estado, EstadoPago.ANULADO_POR_USUARIO)
        self.tx.commit.assert_not_called()
        self.assertEqual(self.cupos(), 3)

    def test_timeout(self):
        pago = self.iniciar(self.matricula_pendiente())
        resultado = servicios.procesar_retorno(
            {"TBK_ORDEN_COMPRA": pago.buy_order, "TBK_ID_SESION": pago.session_id}
        )
        self.assertEqual(resultado.estado, EstadoPago.EXPIRADO)
        self.tx.commit.assert_not_called()

    def test_error_de_formulario_no_hace_commit(self):
        pago = self.iniciar(self.matricula_pendiente())
        resultado = servicios.procesar_retorno({"token_ws": pago.token, "TBK_TOKEN": pago.token})
        self.assertEqual(resultado.estado, EstadoPago.ERROR)
        self.tx.commit.assert_not_called()

    def test_anulacion_no_pisa_un_pago_ya_aprobado(self):
        pago = self.iniciar(self.matricula_pendiente())
        self.aprobar_en_transbank(pago)
        servicios.confirmar_pago_webpay(pago.token)
        resultado = servicios.procesar_retorno({"TBK_TOKEN": pago.token})
        self.assertEqual(resultado.estado, EstadoPago.APROBADO)

    def test_retorno_sin_parametros(self):
        self.assertIsNone(servicios.procesar_retorno({}))


class IdempotenciaYReembolsoTests(BasePagosTests):
    def test_token_procesado_dos_veces_no_descuenta_dos_veces(self):
        pago = self.iniciar(self.matricula_pendiente())
        self.aprobar_en_transbank(pago)
        servicios.confirmar_pago_webpay(pago.token)
        otra_vez = servicios.confirmar_pago_webpay(pago.token)
        self.assertEqual(otra_vez.estado, EstadoPago.APROBADO)
        self.assertEqual(self.tx.commit.call_count, 1)
        self.assertEqual(self.cupos(), 2)
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_monto_que_no_coincide_reembolsa(self):
        matricula = self.matricula_pendiente()
        pago = self.iniciar(matricula)
        self.aprobar_en_transbank(pago, monto=1)
        resultado = servicios.confirmar_pago_webpay(pago.token)
        self.assertEqual(resultado.estado, EstadoPago.REEMBOLSADO)
        self.tx.refund.assert_called_once_with(pago.token, 1)
        matricula.refresh_from_db()
        self.assertEqual(matricula.estado, EstadoMatricula.PENDIENTE)
        self.assertEqual(self.cupos(), 3)

    def test_aprobado_sin_cupos_reembolsa_y_matricula_sigue_pendiente(self):
        matricula = self.matricula_pendiente()
        pago = self.iniciar(matricula)
        Curso.objects.filter(pk=self.curso.pk).update(cupos_disponibles=0)  # otro estudiante tomó el último
        self.aprobar_en_transbank(pago)
        resultado = servicios.confirmar_pago_webpay(pago.token)
        self.assertEqual(resultado.estado, EstadoPago.REEMBOLSADO)
        self.assertIn("No hay cupos disponibles", resultado.respuesta_cruda["motivo"])
        self.tx.refund.assert_called_once_with(pago.token, 120000)
        matricula.refresh_from_db()
        self.assertEqual(matricula.estado, EstadoMatricula.PENDIENTE)
        self.assertEqual(self.cupos(), 0)
        self.assertFalse(Inscripcion.objects.exists())

    def test_aprobado_con_curso_inactivo_reembolsa(self):
        pago = self.iniciar(self.matricula_pendiente())
        Curso.objects.filter(pk=self.curso.pk).update(activo=False)
        self.aprobar_en_transbank(pago)
        self.assertEqual(servicios.confirmar_pago_webpay(pago.token).estado, EstadoPago.REEMBOLSADO)

    def test_dos_pagos_aprobados_de_la_misma_matricula_el_segundo_se_reembolsa(self):
        matricula = self.matricula_pendiente()
        primero, segundo = self.iniciar(matricula), self.iniciar(matricula)
        self.aprobar_en_transbank(primero, segundo)
        self.assertEqual(servicios.confirmar_pago_webpay(primero.token).estado, EstadoPago.APROBADO)
        resultado = servicios.confirmar_pago_webpay(segundo.token)
        self.assertEqual(resultado.estado, EstadoPago.REEMBOLSADO)
        self.tx.refund.assert_called_once_with(segundo.token, 120000)
        matricula.refresh_from_db()
        self.assertEqual(matricula.estado, EstadoMatricula.PAGADO)
        self.assertEqual(self.cupos(), 2)  # el cupo se descontó una sola vez
        self.assertEqual(Inscripcion.objects.count(), 1)
        self.assertEqual(PagoWebpay.objects.filter(estado=EstadoPago.APROBADO).count(), 1)

    def test_si_el_refund_falla_el_pago_queda_en_error_marcado(self):
        pago = self.iniciar(self.matricula_pendiente())
        Curso.objects.filter(pk=self.curso.pk).update(cupos_disponibles=0)
        self.aprobar_en_transbank(pago)
        self.tx.refund.side_effect = TransbankError("sin conexión", 500)
        resultado = servicios.confirmar_pago_webpay(pago.token)
        self.assertEqual(resultado.estado, EstadoPago.ERROR)
        self.assertIn("reembolso_pendiente", resultado.respuesta_cruda)

    def test_no_se_puede_iniciar_pago_de_matricula_ya_pagada(self):
        matricula = self.matricula_pendiente()
        servicios_matricula.pagar_matricula(matricula, self.coordinador, "Pago manual.")
        with self.assertRaises(servicios.MatriculaNoPagableError):
            servicios.iniciar_pago_webpay(matricula, RETORNO)


class RetornoHttpTests(BasePagosTests):
    """La vista de retorno: GET y POST, sin CSRF, con los 4 casos."""

    def test_post_normal_sin_csrf_muestra_pago_aprobado(self):
        pago = self.iniciar(self.matricula_pendiente())
        self.aprobar_en_transbank(pago)
        cliente = Client(enforce_csrf_checks=True)  # Webpay no puede enviar token CSRF
        r = cliente.post("/pagos/webpay/retorno/", {"token_ws": pago.token})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Pago aprobado")
        self.assertContains(r, "1213")
        self.assertContains(r, "6623")

    def test_get_con_token_tambien_funciona(self):
        pago = self.iniciar(self.matricula_pendiente())
        self.aprobar_en_transbank(pago)
        self.assertContains(self.client.get(f"/pagos/webpay/retorno/?token_ws={pago.token}"), "Pago aprobado")

    def test_anulado_y_timeout_por_http(self):
        pago = self.iniciar(self.matricula_pendiente())
        r = self.client.get(
            f"/pagos/webpay/retorno/?TBK_TOKEN={pago.token}&TBK_ORDEN_COMPRA={pago.buy_order}&TBK_ID_SESION=x"
        )
        self.assertContains(r, "Pago anulado")
        otro = self.iniciar(self.matricula_pendiente(crear_usuario("est2"), crear_curso()))
        r = self.client.get(f"/pagos/webpay/retorno/?TBK_ORDEN_COMPRA={otro.buy_order}&TBK_ID_SESION=x")
        self.assertContains(r, "Se agotó el tiempo")

    def test_token_inventado_o_sin_parametros_no_rompe(self):
        self.assertContains(self.client.post("/pagos/webpay/retorno/", {"token_ws": "inventado"}), "No encontramos el pago")
        self.assertContains(self.client.get("/pagos/webpay/retorno/"), "Faltan los datos")
        self.tx.commit.assert_not_called()


class ApiIniciarPagoTests(BasePagosTests):
    def test_iniciar_desde_el_carro_crea_o_reutiliza_la_matricula_pendiente(self):
        servicios_carro.agregar_curso(self.estudiante, self.curso)
        autenticar(self.client, self.estudiante)
        r = self.client.post("/api/matriculas/webpay/iniciar/")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["url"], r.data["monto"]), (URL_WEBPAY, 120000))
        self.assertTrue(r.data["token"])
        self.assertEqual(self.tx.create.call_args.args[3], RETORNO)
        self.assertEqual(self.cupos(), 3)  # iniciar el pago no descuenta cupos
        self.client.post("/api/matriculas/webpay/iniciar/")  # reintento: misma matrícula
        self.assertEqual(Matricula.objects.count(), 1)
        self.assertEqual(PagoWebpay.objects.count(), 2)

    def test_carro_vacio_400(self):
        autenticar(self.client, self.estudiante)
        self.assertEqual(self.client.post("/api/matriculas/webpay/iniciar/").status_code, 400)

    def test_iniciar_matricula_pendiente_propia(self):
        matricula = self.matricula_pendiente()
        autenticar(self.client, self.estudiante)
        r = self.client.post(f"/api/matriculas/{matricula.pk}/webpay/iniciar/")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["matricula_id"], matricula.pk)

    def test_estudiante_no_puede_pagar_matricula_ajena(self):
        matricula = self.matricula_pendiente()
        autenticar(self.client, crear_usuario("intruso"))
        r = self.client.post(f"/api/matriculas/{matricula.pk}/webpay/iniciar/")
        self.assertEqual(r.status_code, 403)
        self.tx.create.assert_not_called()

    def test_coordinador_y_visitante_no_usan_la_api_de_estudiante(self):
        matricula = self.matricula_pendiente()
        self.assertEqual(self.client.post(f"/api/matriculas/{matricula.pk}/webpay/iniciar/").status_code, 401)
        autenticar(self.client, self.coordinador)
        self.assertEqual(self.client.post(f"/api/matriculas/{matricula.pk}/webpay/iniciar/").status_code, 403)

    def test_matricula_inexistente_404(self):
        autenticar(self.client, self.estudiante)
        self.assertEqual(self.client.post("/api/matriculas/999999/webpay/iniciar/").status_code, 404)

    def test_matricula_ya_pagada_409(self):
        matricula = self.matricula_pendiente()
        servicios_matricula.pagar_matricula(matricula, self.coordinador)
        autenticar(self.client, self.estudiante)
        self.assertEqual(self.client.post(f"/api/matriculas/{matricula.pk}/webpay/iniciar/").status_code, 409)


class PanelPagarWebpayTests(BasePagosTests):
    def test_coordinador_inicia_pago_y_recibe_formulario_hacia_webpay(self):
        matricula = self.matricula_pendiente()
        self.client.login(username="coord", password=CLAVE)
        detalle = self.client.get(f"/panel/matriculas/{matricula.pk}/")
        self.assertContains(detalle, "Pagar con Webpay")
        r = self.client.post(f"/panel/matriculas/{matricula.pk}/pagar-webpay/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="token_ws"')
        self.assertContains(r, URL_WEBPAY)

    def test_boton_no_aparece_sin_sesion_ni_en_matriculas_pagadas(self):
        matricula = self.matricula_pendiente()
        self.assertNotContains(self.client.get(f"/panel/matriculas/{matricula.pk}/"), "Pagar con Webpay")
        servicios_matricula.pagar_matricula(matricula, self.coordinador)
        self.client.login(username="coord", password=CLAVE)
        self.assertNotContains(self.client.get(f"/panel/matriculas/{matricula.pk}/"), "Pagar con Webpay")

    def test_visitante_y_estudiante_son_redirigidos_al_login(self):
        matricula = self.matricula_pendiente()
        url = f"/panel/matriculas/{matricula.pk}/pagar-webpay/"
        self.assertTrue(self.client.post(url)["Location"].startswith("/panel/login/"))
        self.client.login(username="est", password=CLAVE)
        self.assertTrue(self.client.post(url)["Location"].startswith("/panel/login/"))
        self.tx.create.assert_not_called()


class ConfirmarMatriculaSigueIgualTests(BasePagosTests):
    """La refactorización no cambió el comportamiento de confirmar_matricula."""

    def test_confirmar_matricula_sigue_pagando_en_un_paso(self):
        servicios_carro.agregar_curso(self.estudiante, self.curso)
        matricula = servicios_matricula.confirmar_matricula(self.estudiante)
        self.assertEqual(matricula.estado, EstadoMatricula.PAGADO)
        self.assertIsNotNone(matricula.pagada_en)
        self.assertEqual(self.cupos(), 2)
        self.assertEqual(Inscripcion.objects.count(), 1)
        self.assertEqual(servicios_carro.obtener_carro(self.estudiante).items.filter(activo=True).count(), 0)
        textos = list(matricula.historial.values_list("observacion", flat=True))
        self.assertIn("Pago aprobado (simulado).", textos)

    def test_crear_pendiente_no_toca_cupos_ni_carro_y_se_reutiliza(self):
        servicios_carro.agregar_curso(self.estudiante, self.curso)
        primera = servicios_matricula.crear_matricula_pendiente(self.estudiante)
        segunda = servicios_matricula.crear_matricula_pendiente(self.estudiante)
        self.assertEqual(primera.pk, segunda.pk)
        self.assertEqual(primera.estado, EstadoMatricula.PENDIENTE)
        self.assertEqual(self.cupos(), 3)
        self.assertEqual(servicios_carro.obtener_carro(self.estudiante).items.filter(activo=True).count(), 1)
        otro = crear_curso(cupos=2)
        servicios_carro.agregar_curso(self.estudiante, otro)  # cursos distintos -> orden nueva
        self.assertNotEqual(servicios_matricula.crear_matricula_pendiente(self.estudiante).pk, primera.pk)

    def test_pagar_matricula_rechaza_matricula_que_ya_no_esta_pendiente(self):
        matricula = self.matricula_pendiente()
        servicios_matricula.pagar_matricula(matricula)
        with self.assertRaises(servicios_matricula.TransicionInvalidaError):
            servicios_matricula.pagar_matricula(matricula)
        self.assertEqual(self.cupos(), 2)
