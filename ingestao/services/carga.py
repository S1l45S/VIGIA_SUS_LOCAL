import csv

from django_mongodb_backend import transaction

from ingestao.models import (
    CargaDeDados,
    RegistroSemanal,
)

from dominio.models import (
    Agravo,
    Municipio,
)

from ingestao.services.validacao import (
    validar_estrutura,
    validar_registro,
    ErroEsquemaCSV,
)


def importar_csv(caminho):

    rejeicoes = []
    registros = []

    origem = str(caminho)

    # 1. Ler e validar o arquivo antes da persistência.

    try:

        with open(
            caminho,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as arquivo:

            leitor = validar_estrutura(arquivo)

            for numero, linha in enumerate(leitor, start=2):

                try:

                    registro = validar_registro(linha)

                    agravo = Agravo.objects.filter(
                        codigo=registro["agravo_codigo"],
                        ativo=True
                    ).first()

                    municipio = Municipio.objects.filter(
                        codigo_ibge=registro["municipio_codigo"],
                        ativo=True
                    ).first()

                    if agravo is None:
                        raise ValueError("Agravo não cadastrado.")

                    if municipio is None:
                        raise ValueError("Município não cadastrado.")

                    if agravo.nome != linha["agravo_nome"].strip():
                        raise ValueError("Nome do agravo divergente.")

                    if municipio.nome != linha["municipio_nome"].strip():
                        raise ValueError("Nome do município divergente.")

                    registro["numero_linha"] = numero
                    registros.append(registro)

                except (ValueError, TypeError) as erro:

                    rejeicoes.append({
                        "linha": numero,
                        "motivo": str(erro),
                    })

    except (OSError, UnicodeError, ErroEsquemaCSV) as erro:

        carga = CargaDeDados.objects.create(
            origem=origem,
            status="REJEITADA",
            motivo_rejeicao=str(erro),
        )

        return carga

    # 2. Não aceitar arquivos sem registros válidos.

    if not registros:

        carga = CargaDeDados.objects.create(
            origem=origem,
            status="REJEITADA",
            registros_lidos=len(rejeicoes),
            registros_rejeitados=len(rejeicoes),
            motivo_rejeicao="Nenhum registro válido.",
        )

        return carga

    # 3. Persistir tudo em uma única transação.

    try:

        with transaction.atomic():

            carga = CargaDeDados.objects.create(
                origem=origem,
                status="PROCESSANDO",
                registros_lidos=len(registros) + len(rejeicoes),
                registros_validos=len(registros),
                registros_rejeitados=len(rejeicoes),
            )

            for registro in registros:

                RegistroSemanal.objects.update_or_create(

                    agravo_codigo=registro["agravo_codigo"],

                    municipio_codigo=registro["municipio_codigo"],

                    semana_inicio=registro["semana_inicio"],

                    defaults={

                        "semana_ord": registro["semana_ord"],

                        "ano": registro["ano"],

                        "semana_epidemiologica": (
                            registro["semana_epidemiologica"]
                        ),

                        "quantidade": registro["quantidade"],

                        "carga_id": str(carga.pk),

                    }

                )

            carga.status = "ACEITA"

            carga.save(update_fields=["status"])

        return carga

    except Exception as erro:

        # A transação já foi revertida quando chegamos aqui.
        # Registrar a falha fora da transação original.

        CargaDeDados.objects.create(
            origem=origem,
            status="REJEITADA",
            registros_lidos=len(registros) + len(rejeicoes),
            registros_validos=0,
            registros_rejeitados=len(rejeicoes),
            motivo_rejeicao=str(erro),
        )

        raise