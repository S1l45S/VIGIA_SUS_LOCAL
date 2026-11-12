from django.core.management.base import BaseCommand, CommandError

from dominio.models import Agravo, Municipio
from ingestao.fontes.pysus import baixar_sinan_pysus
from ingestao.fontes.sinan import FonteSinan
from ingestao.services.calendario import ano_semana_de_texto
from ingestao.services.preparacao import preparar_csv


class Command(BaseCommand):

    help = (
        "Baixa notificações do SINAN, agrega por semana epidemiológica e "
        "grava o CSV normalizado. Não grava nada no banco."
    )

    def add_arguments(self, parser):

        parser.add_argument("--doenca", required=True,
                            help="Código da doença no PySUS, por exemplo DENG.")
        parser.add_argument("--agravo-codigo", required=True,
                            help="Código do agravo no SINAN, por exemplo A90.")
        parser.add_argument("--ano-inicial", required=True, type=int)
        parser.add_argument("--ano-final", required=True, type=int)
        parser.add_argument("--inicio", required=True,
                            help="Primeira semana, no formato AAAASS.")
        parser.add_argument("--fim", default=None,
                            help="Última semana, AAAASS. Se omitida, usa a "
                                 "última da fonte menos --cortar-ultimas.")
        parser.add_argument("--cortar-ultimas", type=int, default=4)
        parser.add_argument("--uf", default="SE")
        parser.add_argument("--municipio", default=None,
                            help="Código IBGE de 7 dígitos. Padrão: todos da UF.")
        parser.add_argument("--saida", required=True, help="Caminho do CSV.")

    def handle(self, *args, **options):

        try:
            inicio = ano_semana_de_texto(options["inicio"])
            fim = (
                ano_semana_de_texto(options["fim"]) if options["fim"] else None
            )
        except ValueError as erro:
            raise CommandError(str(erro)) from erro

        agravo = Agravo.objects.filter(
            codigo=options["agravo_codigo"], ativo=True
        ).first()
        if agravo is None:
            raise CommandError(
                "Agravo não cadastrado. Rode popular_catalogos antes."
            )

        consulta = Municipio.objects.filter(
            uf=options["uf"].upper(), ativo=True
        )
        if options["municipio"]:
            consulta = consulta.filter(codigo_ibge=options["municipio"])
        municipios = {item.codigo_ibge: item.nome for item in consulta}
        if not municipios:
            raise CommandError(
                "Nenhum município no recorte. Rode popular_catalogos antes."
            )

        # unica linha que escolhe a fonte concreta
        fonte = FonteSinan(options["doenca"], baixar=baixar_sinan_pysus)

        anos = range(options["ano_inicial"], options["ano_final"] + 1)
        try:
            resultado, metadados, _ = preparar_csv(
                fonte,
                agravo_codigo=agravo.codigo,
                agravo_nome=agravo.nome,
                municipios=municipios,
                anos=anos,
                inicio=inicio,
                fim=fim,
                cortar_ultimas=options["cortar_ultimas"],
                saida=options["saida"],
            )
        except Exception as erro:
            raise CommandError(f"Falha ao preparar a carga: {erro}") from erro

        self.stdout.write(self.style.SUCCESS(f"CSV gerado: {options['saida']}"))
        self.stdout.write(f"Período: {metadados['periodo']['inicio']} a "
                          f"{metadados['periodo']['fim']}")
        self.stdout.write(f"Linhas lidas: {metadados['linhas_lidas']}")
        self.stdout.write(
            f"Notificações contadas: {resultado.notificacoes_contadas}"
        )
        self.stdout.write(f"Descartes: {metadados['descartes']}")