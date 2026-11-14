from pathlib import Path
from types import SimpleNamespace

from ingestao.fontes.pysus import _como_lista


def test_como_lista_aceita_um_caminho_so():
    assert _como_lista("a.parquet") == ["a.parquet"]
    assert _como_lista(Path("a.parquet")) == [Path("a.parquet")]


def test_como_lista_aceita_lista_de_caminhos():
    assert _como_lista(["a.parquet", "b.parquet"]) == ["a.parquet", "b.parquet"]


def test_como_lista_aceita_o_objeto_do_pysus_com_paths():
    resultado = SimpleNamespace(paths=["/cache/a.parquet"])

    assert _como_lista(resultado) == ["/cache/a.parquet"]
