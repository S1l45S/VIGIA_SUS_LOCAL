from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ingestao.services.carga import importar_csv


class Command(BaseCommand):

    help = "Importa dados epidemiológicos de um arquivo CSV."

    def add_arguments(self, parser):

        parser.add_argument(
            "--arquivo",
            required=True,
            type=str,
            help="Caminho do arquivo CSV.",
        )

    def handle(self, *args, **options):

        caminho = Path(options["arquivo"])

        if not caminho.exists():

            raise CommandError(
                f"Arquivo não encontrado: {caminho}"
            )

        try:

            carga = importar_csv(caminho)

            if carga.status == "REJEITADA":

                self.stdout.write(
                    self.style.ERROR(
                        f"Carga rejeitada: {carga.motivo_rejeicao}"
                    )
                )

                return

            self.stdout.write(
                self.style.SUCCESS(
                    f"Carga concluída: {carga.pk}"
                )
            )

            self.stdout.write(
                f"Registros lidos: {carga.registros_lidos}"
            )

            self.stdout.write(
                f"Registros válidos: {carga.registros_validos}"
            )

            self.stdout.write(
                f"Registros rejeitados: {carga.registros_rejeitados}"
            )

        except Exception as erro:

            raise CommandError(
                f"Falha na ingestão: {erro}"
            ) from erro