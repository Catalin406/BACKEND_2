# ============================================================
# SETTINGS.PY / CONFIGURACIÓN CENTRAL DEL PROYECTO
# Define apps, base de datos PostgreSQL, autenticación JWT, DRF,
# filtros, documentación OpenAPI y localización chilena.
# Todos los datos sensibles y personales se leen desde .env con
# python-decouple: nunca se escriben en el código.
# ============================================================
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# SEGURIDAD BÁSICA
# SECRET_KEY, DEBUG y ALLOWED_HOSTS vienen del archivo .env para
# poder cambiar de entorno sin tocar el código.
# ============================================================
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ============================================================
# DATOS DE LA ALUMNA Y NOMBRE COMERCIAL
# Se exponen a las plantillas con core.context_processors.datos_alumno
# y se reutilizan en la descripción de Swagger y en la raíz de la API.
# ============================================================
ALUMNO_NOMBRE = config("ALUMNO_NOMBRE", default="Catalina Quezada Sanzana")
ALUMNO_SECCION = config("ALUMNO_SECCION", default="IEC-N4-C2")
ALUMNO_ANIO = config("ALUMNO_ANIO", default="2026")
NOMBRE_COMERCIAL = config("NOMBRE_COMERCIAL", default="CodeLab Academy")

# ============================================================
# APLICACIONES INSTALADAS
# Apps de Django, librerías de terceros (DRF, JWT con blacklist,
# django-filter, drf-spectacular) y las apps propias del dominio.
# "core" va primero para que su comando runserver (que evita el 404
# en /static/) reemplace al de django.contrib.staticfiles.
# ============================================================
INSTALLED_APPS = [
    "core",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    # Propias (core está al inicio de la lista)
    "usuarios.apps.UsuariosConfig",
    "cursos",
    "carro",
    "matriculas",
]

# ============================================================
# MIDDLEWARE
# RedireccionNoEncontradaMiddleware va al final para interceptar
# cualquier 404 de las vistas HTML y mostrar la pantalla de redirección.
# ============================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RedireccionNoEncontradaMiddleware",
]

ROOT_URLCONF = "academia_bootcamps.urls"

# ============================================================
# PLANTILLAS
# Carpeta global templates/ (herencia desde base.html) y el context
# processor que inyecta nombre, sección y año de la alumna.
# ============================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.datos_alumno",
            ],
        },
    },
]

WSGI_APPLICATION = "academia_bootcamps.wsgi.application"

# ============================================================
# BASE DE DATOS: POSTGRESQL (driver psycopg 3)
# La pauta exige PostgreSQL; las credenciales viven en .env.
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# ============================================================
# USUARIO PERSONALIZADO Y VALIDACIÓN DE CONTRASEÑAS
# ============================================================
AUTH_USER_MODEL = "usuarios.Usuario"

# ------------------------------------------------------------
# Sesión del panel HTML (la API sigue usando JWT)
# ------------------------------------------------------------
LOGIN_URL = "panel_login"
LOGIN_REDIRECT_URL = "panel"
LOGOUT_REDIRECT_URL = "inicio"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================
# LOCALIZACIÓN (CHILE)
# ============================================================
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# ============================================================
# ARCHIVOS ESTÁTICOS (STORAGES reemplaza a STATICFILES_STORAGE)
# ============================================================
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================
# MENSAJES FLASH: se mapean a las clases de alerta de Bootstrap
# ============================================================
from django.contrib.messages import constants as mensajes  # noqa: E402

MESSAGE_TAGS = {mensajes.ERROR: "danger"}

# ============================================================
# DJANGO REST FRAMEWORK
# JWT por defecto, todo protegido salvo que la vista declare AllowAny,
# filtros/búsqueda/orden globales, paginación de 10 y errores JSON
# uniformes en español mediante el manejador propio.
# ============================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.excepciones.manejador_excepciones_api",
    "DATE_FORMAT": "%d-%m-%Y",
    "DATE_INPUT_FORMATS": ["%Y-%m-%d", "%d-%m-%Y"],
}

# ============================================================
# SIMPLE JWT
# Access corto (30 min), refresh de 1 día con rotación y blacklist
# para que el logout invalide el refresh de verdad.
# ============================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "usuarios.tokens.TokenConRolSerializer",
}

# ============================================================
# DRF-SPECTACULAR (OpenAPI 3 + Swagger UI + ReDoc)
# La descripción incluye datos de la alumna, autenticación, matriz
# de roles y credenciales de prueba.
# ============================================================
SPECTACULAR_SETTINGS = {
    "TITLE": f"{NOMBRE_COMERCIAL} · API de Matrículas",
    "DESCRIPTION": f"""
API REST de la plataforma de reservas de cursos y bootcamps **{NOMBRE_COMERCIAL}**.

**Alumna:** {ALUMNO_NOMBRE} · **Sección:** {ALUMNO_SECCION} · **Año:** {ALUMNO_ANIO}

### Cómo autenticarse
1. Ejecuta `POST /api/auth/login/` con `username` y `password`.
2. Copia el valor `access` de la respuesta.
3. Presiona **Authorize** (arriba a la derecha), pega el token y confirma.
4. El token dura 30 minutos; renuévalo con `POST /api/auth/refresh/`.

### Matriz de roles
| Rol | Endpoints |
|---|---|
| Público | `GET /api/cursos/`, `GET /api/areas/` |
| Estudiante | `GET/POST/DELETE /api/carro-matricula/`, `POST /api/matriculas/confirmar/`, `GET /api/mis-matriculas/` |
| Coordinador | `POST/PUT/DELETE /api/cursos/`, `PATCH /api/matriculas/{{id}}/estado/` |

### Credenciales de prueba
| Usuario | Contraseña | Rol |
|---|---|---|
| `coordinador` | `Coordinador2026!` | Coordinador Académico |
| `estudiante1` | `Estudiante2026!` | Estudiante |
| `estudiante2` | `Estudiante2026!` | Estudiante |
| `estudiante3` | `Estudiante2026!` | Estudiante |
""",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
    "ENUM_NAME_OVERRIDES": {
        "EstadoMatriculaEnum": "matriculas.models.EstadoMatricula",
        "RolEnum": "usuarios.models.Rol",
        "TipoCursoEnum": "cursos.models.TipoCurso",
        "ModalidadEnum": "cursos.models.Modalidad",
    },
    "CONTACT": {"name": f"{ALUMNO_NOMBRE} · {ALUMNO_SECCION}"},
    "TAGS": [
        {"name": "Autenticación", "description": "Registro, login JWT con claims de rol, refresh, logout y perfil."},
        {"name": "Oferta académica", "description": "Áreas de conocimiento y cursos/bootcamps."},
        {"name": "Carro de matrícula", "description": "Carro persistente del estudiante (1 a 1)."},
        {"name": "Matrículas", "description": "Confirmación, estados, cupos e inscripciones UUID."},
        {"name": "Usuarios", "description": "Administración de usuarios (solo coordinador)."},
        {"name": "General", "description": "Raíz de la API."},
    ],
}
