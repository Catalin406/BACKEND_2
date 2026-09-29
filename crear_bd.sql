-- ============================================================
-- CREAR_BD.SQL / CREACIÓN DEL ROL Y LA BASE DE DATOS
-- Ejecutar como superusuario (postgres) con psql:
--   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -f crear_bd.sql
-- Crea el rol "catalina" con permiso CREATEDB (necesario para que
-- "manage.py test" cree la base de pruebas) y la base
-- academia_bootcamps_db en UTF8. Es idempotente: si el rol o la base
-- ya existen, no falla.
-- ============================================================

-- ============================================================
-- ROL DE LA APLICACIÓN
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'catalina') THEN
        CREATE ROLE catalina WITH LOGIN PASSWORD '5678' CREATEDB;
    ELSE
        ALTER ROLE catalina WITH LOGIN CREATEDB;
    END IF;
END
$$;

-- ============================================================
-- BASE DE DATOS (CREATE DATABASE no puede ir dentro de DO,
-- por eso se usa \gexec de psql para crearla solo si falta)
-- ============================================================
SELECT 'CREATE DATABASE academia_bootcamps_db OWNER catalina ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'academia_bootcamps_db')\gexec

GRANT ALL PRIVILEGES ON DATABASE academia_bootcamps_db TO catalina;
