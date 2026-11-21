from django.core.management.base import BaseCommand

from alertas.integracao import sincronizar_alertas


class Command(BaseCommand):
    help = "Emite alertas a partir dos resultados de detecção já gravados (idempotente)."

    def handle(self, *args, **options):
        r = sincronizar_alertas()
        self.stdout.write(self.style.SUCCESS(
            f"Alertas criados: {len(r.criados)} (substituíram {len(r.substituidos)}); "
            f"inalterados: {len(r.inalterados)}."
        ))
        if r.obsoletos:
            self.stdout.write(self.style.WARNING(
                f"{len(r.obsoletos)} alerta(s) aberto(s) cuja semana deixou de ser anomalia "
                "(mantidos; revisar):"
            ))
            for a in r.obsoletos:
                self.stdout.write(f"  - {a} ({a.rotulo_situacao})")
