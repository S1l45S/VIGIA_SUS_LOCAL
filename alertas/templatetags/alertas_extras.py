from django import template

from dashboard.services.consulta import formatar_decimal

register = template.Library()


@register.filter
def decimal_br(valor):
    """Uma casa decimal com vírgula, igual ao dashboard (PB03)."""
    return formatar_decimal(valor)
