import json
import re
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ingestao.sintetica import gerador


def _iso(texto):
    m = re.fullmatch(r"(\d{4})-W(\d{2})", texto)
    if not m:
        raise CommandError("Use o formato AAAA-Www, por exemplo 2024-W42.")
    try:
        return date.fromisocalendar(int(m[1]), int(m[2]), 1)
    except ValueError as erro:
        raise CommandError(f"Semana ISO inválida: {texto}.") from erro


class Command(BaseCommand):
    help = (
        "Gera a base sintética rotulada (dengue, zika, chikungunya, leishmaniose e sífilis "
        "congênita) com surtos injetados. Mesma semente, mesmos arquivos (RNF005)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--semente", type=int, default=gerador.SEMENTE_PADRAO)
        parser.add_argument("--inicio", default="2024-W42",
                            help="Primeira semana ISO (AAAA-Www). Padrão: 2024-W42.")
        parser.add_argument("--semanas", type=int, default=gerador.SEMANAS_PADRAO)
        parser.add_argument("--saida", default="data/sinteticos")

    def handle(self, *args, **opts):
        if opts["semanas"] < gerador.HISTORICO_MINIMO + 10:
            raise CommandError("Use ao menos 22 semanas para haver histórico e surtos.")
        base = gerador.gerar_base(
            semente=opts["semente"], inicio=_iso(opts["inicio"]), semanas=opts["semanas"])
        textos = gerador.serializar(base)
        pasta = Path(opts["saida"])
        pasta.mkdir(parents=True, exist_ok=True)
        s = opts["semente"]
        arquivos = {
            f"base_sintetica_s{s}.csv": textos["base"],
            f"surtos_injetados_s{s}.csv": textos["surtos"],
        }
        base.meta["sha256"] = {nome: gerador.sha256(t) for nome, t in arquivos.items()}
        arquivos[f"base_sintetica_s{s}.meta.json"] = json.dumps(
            base.meta, ensure_ascii=False, indent=2) + "\n"
        cat = gerador.catalogos_texto()
        arquivos["catalogo_municipios.csv"] = cat["municipios"]
        arquivos["catalogo_agravos.csv"] = cat["agravos"]
        for nome, texto in arquivos.items():
            (pasta / nome).write_text(texto, encoding="utf-8", newline="")
        self.stdout.write(self.style.SUCCESS(
            f"{len(base.registros)} registros e {len(base.surtos)} surtos injetados "
            f"(semente {s}) em {pasta}/"))
