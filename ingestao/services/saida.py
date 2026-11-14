"""Gravação do CSV normalizado e do arquivo de metadados"""

import hashlib
import json
from pathlib import Path


def sha256_arquivo(caminho):
    resumo = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def escrever_csv(tabela, caminho):
    """grava o CSV de forma deterministica"""
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(caminho, index=False, encoding="utf-8", lineterminator="\n")


def caminho_metadados(caminho_csv):
    caminho_csv = Path(caminho_csv)
    return caminho_csv.with_name(caminho_csv.name + ".meta.json")


def escrever_metadados(caminho_csv, metadados):
    with open(caminho_metadados(caminho_csv), "w", encoding="utf-8", newline="\n") as arquivo:
        json.dump(metadados, arquivo, ensure_ascii=False, indent=2, sort_keys=True)
        arquivo.write("\n")