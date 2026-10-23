# ============================================================
# USUARIOS/TESTS.PY / PRUEBAS DE JWT, CLAIMS, PERMISOS Y USUARIOS
# Verifica: login con access/refresh y claim "rol", registro solo
# como estudiante, logout con blacklist, matriz de permisos 401/403
# y baja lógica de usuarios (API y HTML).
# ============================================================
import jwt
from django.conf import settings
from rest_framework.test import APITestCase

from carro.models import CarroMatricula
from core.fabricas import CLAVE, autenticar, crear_curso, crear_usuario
from cursos.models import Curso
from usuarios.models import Rol, Usuario


class LoginJWTTests(APITestCase):
    """Login, claims y logout."""

    def setUp(self):
        self.estudiante = crear_usuario("ana", first_name="Ana", last_name="Pérez")
        self.coordinador = crear_usuario("coord", rol=Rol.COORDINADOR)

    # ============================================================
    # LOGIN DEVUELVE TOKENS CON CLAIM ROL
    # ============================================================
    def test_login_devuelve_access_refresh_y_claim_rol(self):
        r = self.client.post("/api/auth/login/", {"username": "ana", "password": CLAVE}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.assertEqual(r.data["rol"], "ESTUDIANTE")
        payload = jwt.decode(r.data["access"], settings.SECRET_KEY, algorithms=["HS256"])
        self.assertEqual(payload["rol"], "ESTUDIANTE")
        self.assertEqual(payload["username"], "ana")
        self.assertEqual(payload["nombre_completo"], "Ana Pérez")

    def test_login_coordinador_claim(self):
        datos = autenticar(self.client, self.coordinador)
        payload = jwt.decode(datos["access"], settings.SECRET_KEY, algorithms=["HS256"])
        self.assertEqual(payload["rol"], "COORDINADOR")
        self.assertTrue(Usuario.objects.get(pk=self.coordinador.pk).is_staff)

    def test_login_invalido_mensaje_espanol(self):
        r = self.client.post("/api/auth/login/", {"username": "ana", "password": "mala"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.data["error"])

    def test_perfil_muestra_claims(self):
        autenticar(self.client, self.estudiante)
        r = self.client.get("/api/auth/perfil/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["claims_token"]["rol"], "ESTUDIANTE")

    def test_logout_invalida_refresh(self):
        datos = autenticar(self.client, self.estudiante)
        r = self.client.post("/api/auth/logout/", {"refresh": datos["refresh"]}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.client.post("/api/auth/refresh/", {"refresh": datos["refresh"]}, format="json")
        self.assertEqual(r.status_code, 401)


class RegistroTests(APITestCase):
    """Registro público."""

    def test_registro_crea_estudiante_con_carro_aunque_pida_coordinador(self):
        r = self.client.post("/api/auth/registro/", {
            "username": "nuevo", "email": "nuevo@prueba.cl", "password": "OtraClave2026!",
            "password_confirmacion": "OtraClave2026!", "rol": "COORDINADOR",
        }, format="json")
        self.assertEqual(r.status_code, 201)
        usuario = Usuario.objects.get(username="nuevo")
        self.assertEqual(usuario.rol, Rol.ESTUDIANTE)
        self.assertTrue(usuario.check_password("OtraClave2026!"))
        self.assertTrue(CarroMatricula.objects.filter(estudiante=usuario).exists())

    def test_registro_rechaza_contrasena_debil(self):
        r = self.client.post("/api/auth/registro/", {
            "username": "debil", "email": "debil@prueba.cl", "password": "123",
            "password_confirmacion": "123",
        }, format="json")
        self.assertEqual(r.status_code, 400)


class MatrizPermisosTests(APITestCase):
    """Matriz de roles: público, estudiante y coordinador."""

    def setUp(self):
        self.estudiante = crear_usuario("est")
        self.coordinador = crear_usuario("coord", rol=Rol.COORDINADOR)
        self.curso = crear_curso()
        self.datos_curso = {
            "titulo": "Nuevo", "descripcion": "d", "area": self.curso.area_id, "tipo": "TALLER",
            "modalidad": "ONLINE", "costo_matricula": 50000, "fecha_inicio": "2027-05-01",
            "fecha_termino": "2027-05-02", "cupos_maximos": 5,
        }

    def test_anonimo_lee_cursos_y_areas(self):
        self.assertEqual(self.client.get("/api/cursos/").status_code, 200)
        self.assertEqual(self.client.get("/api/areas/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/cursos/{self.curso.pk}/").status_code, 200)

    def test_anonimo_no_escribe_401(self):
        self.assertEqual(self.client.post("/api/cursos/", self.datos_curso, format="json").status_code, 401)
        self.assertEqual(self.client.delete(f"/api/cursos/{self.curso.pk}/").status_code, 401)
        self.assertEqual(self.client.get("/api/carro-matricula/").status_code, 401)
        self.assertEqual(self.client.patch("/api/matriculas/1/estado/", {"estado": "CANCELADO"}).status_code, 401)

    def test_estudiante_no_crea_cursos_ni_cambia_estados_403(self):
        autenticar(self.client, self.estudiante)
        self.assertEqual(self.client.post("/api/cursos/", self.datos_curso, format="json").status_code, 403)
        self.assertEqual(self.client.patch("/api/matriculas/1/estado/", {"estado": "CANCELADO"}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 403)

    def test_coordinador_no_usa_carro_403(self):
        autenticar(self.client, self.coordinador)
        self.assertEqual(self.client.get("/api/carro-matricula/").status_code, 403)
        self.assertEqual(self.client.post("/api/matriculas/confirmar/").status_code, 403)

    def test_coordinador_crea_edita_y_desactiva_curso(self):
        autenticar(self.client, self.coordinador)
        r = self.client.post("/api/cursos/", self.datos_curso, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["cupos_disponibles"], 5)
        r = self.client.put(f"/api/cursos/{r.data['id']}/", {**self.datos_curso, "cupos_maximos": 8}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["cupos_disponibles"], 8)
        r = self.client.delete(f"/api/cursos/{self.curso.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk, activo=False).exists())

    def test_rol_revocado_invalida_token_antiguo(self):
        autenticar(self.client, self.coordinador)
        Usuario.objects.filter(pk=self.coordinador.pk).update(rol=Rol.ESTUDIANTE)
        self.assertEqual(self.client.post("/api/cursos/", self.datos_curso, format="json").status_code, 403)


class UsuariosCrudTests(APITestCase):
    """CRUD de usuarios con baja lógica."""

    def setUp(self):
        self.coordinador = crear_usuario("coord", rol=Rol.COORDINADOR)
        self.estudiante = crear_usuario("est")

    def test_delete_api_no_borra_fila(self):
        autenticar(self.client, self.coordinador)
        r = self.client.delete(f"/api/usuarios/{self.estudiante.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Usuario.objects.filter(pk=self.estudiante.pk, is_active=False).exists())
        r = self.client.post(f"/api/usuarios/{self.estudiante.pk}/reactivar/")
        self.assertTrue(Usuario.objects.get(pk=self.estudiante.pk).is_active)

    def test_coordinador_ve_carro_de_estudiante(self):
        autenticar(self.client, self.coordinador)
        r = self.client.get(f"/api/usuarios/{self.estudiante.pk}/carro-matricula/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["cantidad_cursos"], 0)

    def test_crear_usuario_html_con_rol_y_password_hasheada(self):
        self.client.login(username="coord", password=CLAVE)
        r = self.client.post("/panel/usuarios/nuevo/", {
            "username": "html", "first_name": "H", "last_name": "T", "email": "html@prueba.cl",
            "rut": "", "telefono": "", "rol": "COORDINADOR", "password1": "HtmlClave2026!", "password2": "HtmlClave2026!",
        })
        self.assertEqual(r.status_code, 302)
        usuario = Usuario.objects.get(username="html")
        self.assertTrue(usuario.check_password("HtmlClave2026!"))
        self.assertTrue(usuario.is_staff)

    def test_desactivar_html_no_borra_fila(self):
        self.client.login(username="coord", password=CLAVE)
        r = self.client.post(f"/panel/usuarios/{self.estudiante.pk}/desactivar/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Usuario.objects.filter(pk=self.estudiante.pk, is_active=False).exists())


# ============================================================
# SEGURIDAD DEL PANEL HTML
# Lectura abierta; cualquier escritura exige sesión de coordinador.
# Un visitante o un estudiante logueado son redirigidos al login y
# NO se modifica nada (se comprueba contra la base de datos).
# ============================================================
class PanelSeguridadTests(APITestCase):
    """Login/logout del panel y decorador solo_coordinador_para_escribir."""

    def setUp(self):
        self.coordinador = crear_usuario("coord", rol=Rol.COORDINADOR)
        self.estudiante = crear_usuario("est")
        self.curso = crear_curso()
        self.datos_usuario = {
            "username": "intruso", "first_name": "I", "last_name": "N", "email": "intruso@prueba.cl",
            "rut": "", "telefono": "", "rol": "COORDINADOR", "password1": "Intruso2026!", "password2": "Intruso2026!",
        }

    def _escrituras(self):
        """Un POST de cada app del panel: usuarios, cursos, carros y matrículas."""
        return [
            ("/panel/usuarios/nuevo/", self.datos_usuario),
            (f"/panel/usuarios/{self.estudiante.pk}/desactivar/", {}),
            (f"/panel/cursos/{self.curso.pk}/desactivar/", {}),
            (f"/panel/areas/{self.curso.area.pk}/desactivar/", {}),
            (f"/panel/carros/{self.estudiante.pk}/agregar/", {"curso": self.curso.pk}),
            (f"/panel/carros/{self.estudiante.pk}/confirmar/", {}),
            ("/panel/matriculas/1/estado/", {"estado": "CANCELADO"}),
        ]

    def _nada_cambio(self):
        self.assertFalse(Usuario.objects.filter(username="intruso").exists())
        self.assertTrue(Usuario.objects.get(pk=self.estudiante.pk).is_active)
        self.assertTrue(Curso.objects.get(pk=self.curso.pk).activo)
        self.assertFalse(CarroMatricula.objects.filter(estudiante=self.estudiante, items__isnull=False).exists())

    def test_visitante_sin_sesion_es_redirigido_al_login(self):
        for url, datos in self._escrituras():
            with self.subTest(url=url):
                r = self.client.post(url, datos)
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r["Location"].startswith("/panel/login/?next="), r["Location"])
        self._nada_cambio()

    def test_estudiante_logueado_es_redirigido_al_login(self):
        self.client.login(username="est", password=CLAVE)
        for url, datos in self._escrituras():
            with self.subTest(url=url):
                r = self.client.post(url, datos)
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r["Location"].startswith("/panel/login/?next="), r["Location"])
        self._nada_cambio()

    def test_coordinador_logueado_puede_escribir(self):
        self.client.login(username="coord", password=CLAVE)
        r = self.client.post("/panel/usuarios/nuevo/", self.datos_usuario)
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("/login/", r["Location"])
        self.assertTrue(Usuario.objects.filter(username="intruso").exists())

    def test_lectura_sigue_abierta_sin_sesion(self):
        for ruta in ["/panel/", "/panel/usuarios/", "/panel/cursos/", "/panel/carros/", "/panel/matriculas/",
                     "/panel/usuarios/nuevo/"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_login_panel_solo_coordinador(self):
        r = self.client.post("/panel/login/", {"username": "est", "password": CLAVE})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Solo el Coordinador Académico puede iniciar sesión")
        self.assertNotIn("_auth_user_id", self.client.session)
        r = self.client.post("/panel/login/", {"username": "coord", "password": CLAVE})
        self.assertEqual(r.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_solo_por_post(self):
        self.client.login(username="coord", password=CLAVE)
        self.assertEqual(self.client.get("/panel/logout/").status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.post("/panel/logout/").status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
