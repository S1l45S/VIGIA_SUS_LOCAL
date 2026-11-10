import pytest

from ingestao.services.ibge import com_dv, digito_verificador


@pytest.mark.parametrize(("codigo6", "dv"), [
    ("280030", 8),   # Aracaju
])

def test_digito_verificador_de_municipios_conhecidos(codigo6, dv):
    assert digito_verificador(codigo6) == dv


def test_com_dv_acrescenta_digito_a_codigo_de_seis_digitos():
    assert com_dv("280030") == "2800308"
    assert com_dv(280030) == "2800308"


def test_com_dv_aceita_codigo_de_sete_digitos_correto():
    assert com_dv("2800308") == "2800308"


def test_com_dv_rejeita_digito_verificador_errado():
    with pytest.raises(ValueError, match="verificador"):
        com_dv("2800307")


@pytest.mark.parametrize("codigo", ["", "12345", "12345678", "28003a", "28003.0"])
def test_com_dv_rejeita_formato_invalido(codigo):
    with pytest.raises(ValueError):
        com_dv(codigo)