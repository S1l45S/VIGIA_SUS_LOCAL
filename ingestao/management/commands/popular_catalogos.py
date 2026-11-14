from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dominio.models import Agravo, Municipio
from ingestao.services.catalogos import ErroCatalogo, ler_agravos, ler_municipios


class Command(BaseCommand):

    help = "Cadastra municípios e agravos a partir dos CSV de catálogo."

    def add_arguments(self, parser):

        parser.add_argument(
            "--municipios",
            default="data/catalogos/municipios_se.csv",
            help="CSV com codigo_ibge,nome,uf.",
        )
        parser.add_argument(
            "--agravos",
            default="data/catalogos/agravos.csv",
            help="CSV com codigo,nome.",
        )

    def handle(self, *args, **options):

        for opcao in ("municipios", "agravos"):
            if not Path(options[opcao]).exists():
                raise CommandError(f"Arquivo não encontrado: {options[opcao]}")

        try:
            municipios = ler_municipios(options["municipios"])
            agravos = ler_agravos(options["agravos"])
        except ErroCatalogo as erro:
            raise CommandError(str(erro)) from erro

        for item in municipios:
            Municipio.objects.update_or_create(
                codigo_ibge=item["codigo_ibge"],
                defaults={"nome": item["nome"], "uf": item["uf"], "ativo": True},
            )

        for item in agravos:
            Agravo.objects.update_or_create(
                codigo=item["codigo"],
                defaults={"nome": item["nome"], "ativo": True},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogos atualizados: {len(municipios)} municípios, "
                f"{len(agravos)} agravos."
            )
        )