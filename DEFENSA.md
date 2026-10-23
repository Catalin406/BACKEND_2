# Guía de defensa oral · EVA-2 Desarrollo Backend

**Catalina Quezada Sanzana · Sección IEC-N4-C2 · 2026** — CodeLab Academy (Caso 2: reservas de cursos y bootcamps)

Para cada indicador de la rúbrica: **dónde está** (archivo, clase o función y línea) y **cómo explicarlo**.

---

## 1. Arquitectura, base de datos y modelos

| Qué | Dónde |
|---|---|
| Motor PostgreSQL (psycopg 3), credenciales desde `.env` | `academia_bootcamps/settings.py:110` (`DATABASES`) |
| Usuario personalizado | `settings.py:122` (`AUTH_USER_MODEL = "usuarios.Usuario"`) |
| CHOICES `Rol` | `usuarios/models.py:16` |
| `Usuario` + `save()` que sincroniza `is_staff` con el rol | `usuarios/models.py:29` y `:69` |
| CHOICES `TipoCurso` y `Modalidad` | `cursos/models.py:16` y `:24` |
| `Curso` con `UniqueConstraint` (cohorte) y 4 `CheckConstraint(condition=...)` | `cursos/models.py:76`, `:107`–`:127` |
| Ajuste de cupos al cambiar el máximo (con bloqueo) | `cursos/models.py:173` (`clean`) y `:206` (`save`) |
| `CarroMatricula` 1 a 1 (`OneToOneField`) | `carro/models.py:16`–`:19` |
| Total y cantidad calculados (no guardados, 3FN) | `carro/models.py:45` y `:50` |
| `UniqueConstraint(name="curso_unico_por_carro")` | `carro/models.py:78` |
| CHOICES `EstadoMatricula` | `matriculas/models.py:19` |
| `Matricula` con código UUID, total por anotación `Sum` | `matriculas/models.py:43`, `:46`, `:35` (`con_total`), `:76` |
| `DetalleMatricula` (costo congelado) | `matriculas/models.py:89` |
| `Inscripcion` 1 a 1 con el detalle, UUID único | `matriculas/models.py:120`, `:123`, `:126` |
| `HistorialEstadoMatricula` (auditoría) | `matriculas/models.py:152` |
| Admin con `list_display`, `list_filter`, `search_fields` | `*/admin.py` |

**Cómo explicarlo:** "La base está en 3.ª forma normal: el curso guarda solo la FK del área, el ítem del carro no guarda el precio porque depende del curso, y la inscripción no repite estudiante ni curso porque se obtienen por el detalle. Los totales se calculan con `Sum`. El costo del detalle sí se guarda porque es un hecho histórico: lo que se pagó ese día. Las reglas críticas viven también en la base: si el código fallara, el `CheckConstraint` impide cupos negativos. Nada se borra: todo es baja lógica y las relaciones usan `PROTECT`."

---

## 2. JWT, claims de rol y permisos

| Qué | Dónde |
|---|---|
| Configuración `SIMPLE_JWT` (30 min / 1 día / rotación / blacklist) | `academia_bootcamps/settings.py:190` |
| `REST_FRAMEWORK` (JWT, `IsAuthenticated` por defecto, filtros, paginación, handler) | `settings.py:167` |
| `TokenConRolSerializer.get_token()` agrega `rol`, `username`, `email`, `nombre_completo` | `usuarios/tokens.py:11`, `:23` |
| Respuesta del login con `rol` y `usuario` | `usuarios/tokens.py:36` |
| `LoginConRolView` | `usuarios/views.py:64` |
| Logout con blacklist | `usuarios/views.py:83`, `usuarios/serializers.py:76` |
| Perfil con los claims leídos de `request.auth` | `usuarios/views.py:105` |
| Registro público que fuerza ESTUDIANTE | `usuarios/serializers.py:40` |
| Permiso base que compara el claim del token con la BD | `usuarios/permisos.py:32`–`:38` |
| `EsCoordinador`, `EsEstudiante` | `usuarios/permisos.py:45`, `:52` |
| `EsCoordinadorOSoloLectura` | `usuarios/permisos.py:62` |
| `EsPropietarioDeLaMatricula` (objeto) | `usuarios/permisos.py:76` |
| Errores JSON uniformes en español | `core/excepciones.py:60` (`manejador_excepciones_api`) |

**Cómo explicarlo:** "Al hacer login, el token lleva el rol como claim. Los permisos leen `request.auth.get('rol')` y lo contrastan con el rol real y con `is_active`: si le quito el rol a alguien, su token viejo deja de servir (hay una prueba de eso). Sin token la API responde 401 y con un rol incorrecto, 403. El logout pone el refresh en la blacklist."

---

## 3. Carro de matrícula persistente

| Qué | Dónde |
|---|---|
| Señal `post_save` que crea el carro de cada estudiante | `usuarios/signals.py:14`–`:15` (registrada en `usuarios/apps.py`) |
| `obtener_carro`, `agregar_curso`, `quitar_curso`, `vaciar_carro` | `carro/servicios.py:58`, `:84`, `:125`, `:141` |
| Error de duplicado "Este curso ya está en tu carro de matrícula" | `carro/servicios.py:21` |
| API GET/POST/DELETE | `carro/views.py:22` (`get` `:40`, `post` `:65`, `delete` `:78`) |
| Quitar un ítem | `carro/views.py:83` |
| Panel HTML que usa los mismos servicios | `carro/views_html.py:38`–`:107` |
| Prueba de persistencia tras logout y nuevo login | `carro/tests.py` → `test_carro_persiste_tras_logout_y_nuevo_login` |

**Cómo explicarlo:** "El carro no vive en la sesión ni en el navegador: es una tabla con relación 1 a 1 con el estudiante. Por eso, si cierro sesión, apago el servidor o entro desde otro dispositivo, el carro sigue igual. El duplicado se valida dos veces: en el servicio, con un mensaje claro, y en la base, con `UniqueConstraint`. Agregar al carro no descuenta cupos: solo informa si el curso está agotado."

---

## 4. Confirmación, cupos e inscripciones UUID

| Qué | Dónde |
|---|---|
| Excepciones propias (`CarroVacioError`, `SinCuposError`, `CursoYaInscritoError`, `TransicionInvalidaError`) | `matriculas/servicios.py:28`, `:35`, `:57`, `:64` |
| `confirmar_matricula()` en una sola `transaction.atomic()` | `matriculas/servicios.py:109` |
| Bloqueo del carro `select_for_update()` | `matriculas/servicios.py:116` |
| Bloqueo de los cursos en orden fijo por id | `matriculas/servicios.py:128` |
| Descuento atómico `F("cupos_disponibles") - 1` | `matriculas/servicios.py:171` |
| Emisión de inscripciones UUID | `matriculas/servicios.py:182` |
| `TRANSICIONES_PERMITIDAS` | `matriculas/servicios.py:75` |
| `cambiar_estado_matricula()` y liberación con `F(...) + 1` | `matriculas/servicios.py:198`, `:228`–`:229` |
| API confirmar (201 / 409) y cambio de estado | `matriculas/views.py:38`, `:154` |
| Demostración con dos hilos | `core/management/commands/simular_concurrencia.py` |
| Prueba de concurrencia | `matriculas/tests.py:148` (`ConcurrenciaTests`) |

**Cómo explicarlo:** "Todo ocurre en una transacción. Primero bloqueo el carro para que el mismo estudiante no confirme dos veces. Después bloqueo las filas de los cursos con `SELECT … FOR UPDATE`, siempre en orden por id para evitar interbloqueos. Si dos estudiantes quieren el último cupo al mismo tiempo, el segundo queda esperando; cuando el primero termina, el segundo relee `cupos_disponibles = 0` y se rechaza con 409. Como se lanza una excepción, PostgreSQL hace rollback: no queda matrícula, no cambia ningún cupo y el carro queda intacto. Al cancelar una matrícula pagada, se suma 1 cupo por curso y las inscripciones quedan inactivas."

---

## 5. Filtros y documentación OpenAPI

| Qué | Dónde |
|---|---|
| `CursoFilter` (área, área_nombre, tipo, modalidad, costo_min/max, inicio_desde/hasta, con_cupos) | `cursos/filtros.py:12`, `con_cupos` en `:52` |
| Uso en la API con búsqueda y orden | `cursos/views.py:110`–`:111` |
| Reutilización en la oferta HTML | `cursos/views_html.py:34` |
| `MatriculaFilter` e `InscripcionFilter` | `matriculas/filtros.py:16`, `:37`; uso en `matriculas/views.py:127`, `:177` |
| `SPECTACULAR_SETTINGS` (descripción con alumna, roles y credenciales; `persistAuthorization`) | `settings.py:205`, `:207`, `:236` |
| Ejemplos `OpenApiExample` (login, agregar curso, duplicado 400, confirmar 201, sin cupos 409, cambio de estado) | `usuarios/views.py:50`; `carro/views.py:52`; `matriculas/views.py:50`, `:66`, `:141` |
| Rutas `/api/schema/`, `/api/docs/`, `/api/redoc/` | `academia_bootcamps/urls.py` |
| Swagger y ReDoc con footer | `templates/drf_spectacular/swagger_ui.html`, `redoc.html` |

**Cómo explicarlo:** "El mismo `CursoFilter` sirve a la API y a la página de la oferta, así que filtran igual. drf-spectacular genera OpenAPI 3 y detecta el esquema Bearer de simplejwt; por eso el botón Authorize funciona. `manage.py spectacular --validate --fail-on-warn` da 0 advertencias."

---

## 6. Calidad, comentarios y footer

| Qué | Dónde |
|---|---|
| Context processor con datos de la alumna desde `.env` | `core/context_processors.py:10`, registrado en `settings.py:96` |
| Footer en todas las pantallas | `templates/parciales/footer.html:9` (incluido en `base.html`, Swagger, ReDoc y `rest_framework/api.html`) |
| Paleta en variables CSS que sobrescriben Bootstrap | `static/css/tema.css:14` (paleta) y `:59` (`--bs-primary`) |
| Filtro `|clp` | `core/templatetags/formato.py` |
| Catch-all y `handler404` | `academia_bootcamps/urls.py:73`, `:75` |
| Middleware contra 404 (incluso con DEBUG=True) | `core/middleware.py:11`, `:22`, `:30` |
| Barra final (`/cursos` → `/cursos/`) con `resolve()` | `core/views.py:122`, `:131` |
| `runserver` propio: `/static/` inexistente también va a la redirección | `core/management/commands/runserver.py` (`ManejadorEstaticosConRedireccion`); `core` primero en `INSTALLED_APPS` |
| Helper `obtener_o_redirigir` (sin `get_object_or_404`) | `core/utilidades.py:21` |
| Pruebas: 69, todas aprobadas | `*/tests.py` |

**Cómo explicarlo:** "Cada archivo empieza con un bloque que explica su responsabilidad. Los datos de la alumna nunca están escritos en las plantillas: llegan del `.env` mediante el context processor. Ninguna ruta muestra el 404: hay tres capas (catch-all, `handler404` y middleware), y las pruebas lo comprueban con más de 8 rutas absurdas. Como el servidor de desarrollo atiende `/static/` antes que las URLs, sobrescribí `runserver` con un manejador de estáticos propio que, si el archivo no existe, muestra la misma pantalla de redirección."

---

## 7. Por qué el panel ahora exige login para modificar

| Qué | Dónde |
|---|---|
| Decorador `solo_coordinador_para_escribir` | `usuarios/permisos.py` (final del archivo) |
| Login y logout del panel (`LoginView` / `LogoutView`) | `usuarios/urls.py` (`/panel/login/`, `/panel/logout/`) |
| Formulario que rechaza a quien no es coordinador | `usuarios/forms.py` (`LoginPanelForm`) |
| Plantilla de login | `templates/usuarios/login.html` |
| Autor real en el historial | `matriculas/views_html.py` (`request.user`) y `carro/views_html.py` (`confirmar_matricula(..., autor=request.user)`) |
| Pruebas | `usuarios/tests.py` (`PanelSeguridadTests`) |

**Qué era el problema (IDOR / control de acceso roto).** Las vistas de `/panel/...` no preguntaban quién era el usuario. Bastaba conocer la URL, por ejemplo `POST /panel/usuarios/nuevo/`, para crear un usuario con rol COORDINADOR, o `POST /panel/cursos/3/desactivar/` para dar de baja un curso. Se le llama IDOR (referencia directa a objetos sin control de acceso) porque el sistema entregaba la acción solo por conocer el identificador o la ruta, sin comprobar permisos.

**Por qué es grave en un sitio público.** El servidor ahora está en internet con un dominio HTTPS: cualquier persona o bot que encuentre las rutas puede escalar privilegios (hacerse coordinador), anular matrículas de otros estudiantes (liberando cupos) o desactivar toda la oferta. Además, el historial de matrículas registraba autor vacío, así que ni siquiera se podía saber quién lo hizo.

**Cómo se corrigió.**
1. Login del panel con la sesión de Django en `/panel/login/`. Solo entra el Coordinador Académico; si un estudiante pone su contraseña correcta, recibe el mensaje "Solo el Coordinador Académico puede iniciar sesión en el panel" y no queda con sesión.
2. El decorador `solo_coordinador_para_escribir` deja pasar GET, HEAD y OPTIONS, y para cualquier otro método exige sesión activa con `is_staff` y rol COORDINADOR. Si no la hay, redirige al login con `?next=`. Se aplicó a las 17 vistas de escritura de áreas, cursos, usuarios, carros y matrículas.
3. El logout es solo por POST (Django 5 lo exige), así que otra página no puede cerrar la sesión con un simple enlace.
4. Donde se guardaba el autor de un cambio ahora se usa `request.user`, el coordinador real.

**Por qué la lectura queda abierta.** La pauta del caso define lectura pública (ver oferta, cursos, matrículas) y escritura solo para el Coordinador Académico. El mismo criterio ya existía en la API con `EsCoordinadorOSoloLectura`; ahora el panel HTML lo respeta igual. Los formularios (GET) se pueden ver, pero guardarlos (POST) exige sesión.

**Cómo explicarlo:** "El panel y la API aplican la misma regla: leer es público, escribir es del coordinador. La API lo hace con JWT y el panel con sesión y un decorador. Las pruebas comprueban que un visitante y un estudiante logueado reciben una redirección al login y que no cambia nada en la base de datos."

---

## Guion de demo (5 minutos)

1. **(30 s) Inicio** — `http://127.0.0.1:8000/`: portada con estadísticas reales, footer con nombre, sección y año. Mostrar `settings.py:110` (PostgreSQL).
2. **(45 s) Oferta** — `/cursos/`: filtrar por *Bootcamp* y *Con cupos disponibles*. Abrir un curso: barra de ocupación.
3. **(60 s) Swagger** — `/api/docs/`: `POST /api/auth/login/` con `estudiante2`; pegar el `access` en **jwt.io** para mostrar el claim `rol`; **Authorize**.
4. **(60 s) Carro** — `GET /api/carro-matricula/` (ya tiene el *Taller de Pentesting*, último cupo). `POST` del mismo curso → **400 duplicado**. `POST /api/matriculas/confirmar/` → **201**, estado `PAGADO`, códigos UUID. El taller ahora tiene 0 cupos.
5. **(45 s) Sin cupos** — Login con `estudiante1`, Authorize y `POST /api/matriculas/confirmar/` → **409** "No hay cupos disponibles en «Bootcamp de Ciberseguridad Ofensiva»". Mostrar que su carro sigue intacto.
6. **(40 s) Coordinador** — Login con `coordinador`; `PATCH /api/matriculas/{id}/estado/` con `CANCELADO` sobre la matrícula de `estudiante2` → el taller vuelve a 1 cupo. Repetir con `PAGADO` → **400** (estado final). Con el token de estudiante → **403**.
7. **(30 s) Concurrencia** — en la terminal: `python manage.py simular_concurrencia` → uno PAGADO, otro rechazado, cupos finales 0.
8. **(10 s) Rutas** — abrir `/asdf`: pantalla de redirección y vuelta al inicio en 3 s.

> Para repetir la demo desde cero: `python manage.py seed_data --reset`.
