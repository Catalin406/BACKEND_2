# ============================================================
# CORE/TEMPLATETAGS/FORMATO.PY / FILTROS DE PRESENTACIÓN
# |clp       -> precios en formato chileno ($349.990)
# |clase_estado, |clase_tipo, |clase_modalidad -> clases CSS de los
#               badges (los colores viven solo en static/css/tema.css)
# ============================================================
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


# ============================================================
# PRECIOS EN PESOS CHILENOS
# ============================================================
@register.filter
def clp(valor):
    """Formatea un número como pesos chilenos: 349990 -> $349.990."""
    if valor in (None, ""):
        return "$0"
    try:
        numero = int(Decimal(str(valor)).quantize(Decimal("1")))
    except (InvalidOperation, ValueError, TypeError):
        return valor
    signo = "-" if numero < 0 else ""
    return f"{signo}${abs(numero):,}".replace(",", ".")


# ============================================================
# CLASES CSS PARA BADGES
# ============================================================
@register.filter
def clase_estado(estado):
    """Clase del badge según el estado de la matrícula."""
    return f"badge-estado badge-estado-{str(estado).lower()}"


@register.filter
def clase_tipo(tipo):
    """Clase del badge según el tipo de curso."""
    return f"badge-tipo badge-tipo-{str(tipo).lower()}"


@register.filter
def clase_modalidad(modalidad):
    """Clase del badge según la modalidad."""
    return f"badge-modalidad badge-modalidad-{str(modalidad).lower()}"


@register.filter
def obtener(diccionario, clave):
    """Lee diccionario[clave] dentro de una plantilla."""
    try:
        return diccionario.get(clave)
    except AttributeError:
        return None
