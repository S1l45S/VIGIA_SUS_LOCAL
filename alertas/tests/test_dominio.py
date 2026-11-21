"""RN03 / EST-01 (TR-02..TR-04): teste de transições de estado, sem banco."""
import pytest

from alertas.dominio import (AlertaSubstituido, Situacao, TransicaoInvalida,
                             transicoes_permitidas, validar_transicao)

N, I, E = Situacao.NOVO.value, Situacao.EM_INVESTIGACAO.value, Situacao.ENCERRADO.value


@pytest.mark.parametrize("origem,destino", [(N, I), (I, E), (N, E)])  # TR-02, TR-03, TR-04
def test_transicoes_validas(origem, destino):
    assert validar_transicao(origem, destino) == Situacao(destino)


@pytest.mark.parametrize("origem,destino", [
    (I, N),            # sem retrocesso
    (E, N), (E, I),    # encerrado é terminal (QA-02)
    (N, N), (I, I), (E, E),  # sem mudança
])
def test_transicoes_invalidas(origem, destino):
    with pytest.raises(TransicaoInvalida):
        validar_transicao(origem, destino)


@pytest.mark.parametrize("origem", [N, I, E])
def test_substituido_e_somente_leitura(origem):
    with pytest.raises(AlertaSubstituido):
        validar_transicao(origem, E, substituido=True)
    assert transicoes_permitidas(origem, substituido=True) == frozenset()


def test_situacao_desconhecida():
    with pytest.raises(TransicaoInvalida):
        validar_transicao(N, "arquivado")


def test_permitidas_por_estado():
    assert transicoes_permitidas(N) == {Situacao.EM_INVESTIGACAO, Situacao.ENCERRADO}
    assert transicoes_permitidas(I) == {Situacao.ENCERRADO}
    assert transicoes_permitidas(E) == frozenset()
