import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from deteccao.services.backtest import executar_backtest, relatorio_markdown


def _ler(caminho):
    if not Path(caminho).exists():
        raise CommandError(f"Arquivo não encontrado: {caminho}")
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class Command(BaseCommand):
    help = "Mede detecção de surtos e falsos positivos do detector na base sintética (OBJ02)."

    def add_arguments(self, parser):
        parser.add_argument("--semente", type=int, default=42)
        parser.add_argument("--pasta", default="data/sinteticos")
        parser.add_argument("--janela", type=int, default=8)

    def handle(self, *args, **opts):
        pasta, s = Path(opts["pasta"]), opts["semente"]
        registros = _ler(pasta / f"base_sintetica_s{s}.csv")
        surtos = _ler(pasta / f"surtos_injetados_s{s}.csv")
        meta = json.loads((pasta / f"base_sintetica_s{s}.meta.json").read_text(encoding="utf-8"))
        nomes = {p["codigo"]: p["nome"] for p in meta["perfis_agravos"]}
        resultado = executar_backtest(registros, surtos, janela=opts["janela"])
        texto = relatorio_markdown(resultado, meta, nomes)
        saida = pasta / f"relatorio_backtest_s{s}.md"
        saida.write_text(texto, encoding="utf-8")
        g = resultado["geral"]
        self.stdout.write(
            f"Surtos detectados: {100 * resultado['deteccao_qualquer_semana']:.1f}% | "
            f"FP/alertas: {100 * g['fp_sobre_alertas']:.1f}% | "
            f"FP/semanas normais: {100 * g['fp_sobre_semanas_normais']:.1f}%\n"
            f"Relatório: {saida}")
