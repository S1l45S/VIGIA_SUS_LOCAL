"""Base sintética rotulada (P1 D02 / P2 BaseSinteticaRotulada).

Gera séries semanais de notificações com sazonalidade, tendência, variação entre anos
e municípios e ruído, mais *surtos injetados* documentados (verdade-terreno para medir
OBJ02). Módulo PURO (sem Django, sem numpy): a mesma semente produz exatamente os
mesmos arquivos em qualquer máquina (RNF005).

IMPORTANTE: os dados são fictícios. Os níveis, picos e pesos dos municípios são
ilustrativos e NÃO representam a epidemiologia real; não usar como evidência (R20).
"""

import csv
import hashlib
import io
import json
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta

VERSAO_GERADOR = "1.0"
SEMENTE_PADRAO = 42
SEMANAS_PADRAO = 100  # 20 municípios x 5 agravos x 100 semanas = 10.000 registros (DP11)
INICIO_PADRAO = date.fromisocalendar(2024, 42, 1)  # segunda-feira; termina em 2026-W37
HISTORICO_MINIMO = 12  # nenhum surto começa antes: 8 semanas de janela + folga
INTERVALO_ENTRE_SURTOS = 12
PISO_INCREMENTO_PICO = 4.0  # casos/semana adicionados no pico, mesmo em município pequeno


@dataclass(frozen=True)
class PerfilAgravo:
    codigo: str
    nome: str
    nivel_aracaju: float      # casos/semana esperados na capital (ilustrativo)
    amplitude_sazonal: float  # 0 = sem sazonalidade
    pico_dia_ano: int
    tendencia_anual: float    # variação relativa por ano
    sd_ano: float             # variação entre anos (surtos "naturais" por ano)
    sd_municipio_ano: float
    sd_semana: float          # ruído autorregressivo semanal
    rho: float


# Códigos CID-10 de base; ajuste no catálogo se a fonte oficial usar outro código.
PERFIS = (
    PerfilAgravo("A90", "Dengue", 25.0, 0.60, 105, 0.00, 0.35, 0.25, 0.15, 0.6),
    PerfilAgravo("A92.8", "Zika", 1.5, 0.50, 110, 0.00, 0.30, 0.25, 0.15, 0.5),
    PerfilAgravo("A92.0", "Chikungunya", 8.0, 0.70, 130, 0.00, 0.40, 0.25, 0.15, 0.6),
    PerfilAgravo("B55", "Leishmaniose", 0.8, 0.15, 200, 0.00, 0.20, 0.20, 0.10, 0.3),
    PerfilAgravo("A50", "Sífilis congênita", 2.5, 0.05, 200, 0.06, 0.10, 0.15, 0.10, 0.3),
)

# (código IBGE, nome, peso relativo ilustrativo da população; Aracaju = 1,0).
# Códigos e nomes conferidos na tabela de municípios do IBGE (75 de Sergipe).
MUNICIPIOS = (
    ("2800308", "Aracaju", 1.000),
    ("2804805", "Nossa Senhora do Socorro", 0.300),
    ("2803500", "Lagarto", 0.170),
    ("2802908", "Itabaiana", 0.170),
    ("2806701", "São Cristóvão", 0.160),
    ("2802106", "Estância", 0.110),
    ("2807402", "Tobias Barreto", 0.080),
    ("2807105", "Simão Dias", 0.070),
    ("2800605", "Barra dos Coqueiros", 0.070),
    ("2803005", "Itabaianinha", 0.070),
    ("2804508", "Nossa Senhora da Glória", 0.060),
    ("2805703", "Propriá", 0.050),
    ("2801306", "Capela", 0.050),
    ("2803609", "Laranjeiras", 0.050),
    ("2805406", "Poço Redondo", 0.050),
    ("2801207", "Canindé de São Francisco", 0.045),
    ("2800670", "Boquim", 0.040),
    ("2807600", "Umbaúba", 0.040),
    ("2801405", "Carira", 0.035),
    ("2804409", "Neópolis", 0.030),
)

COLUNAS_BASE = (
    "agravo_codigo", "agravo_nome", "municipio_codigo", "municipio_nome",
    "ano", "semana_epidemiologica", "contagem",
)
COLUNAS_SURTOS = (
    "surto_id", "agravo_codigo", "municipio_codigo", "ano", "semana_epidemiologica",
    "semana_inicio", "duracao_semanas", "fator_pico", "incremento_pico_esperado",
    "incremento_total_esperado", "casos_observados_no_periodo", "semanas_afetadas",
    "semente",
)


# ---------------------------------------------------------------- aleatoriedade
def _rng(semente, *partes) -> random.Random:
    """Fluxo independente por (semente, partes): mudar uma série não altera as outras."""
    texto = "|".join(str(p) for p in (semente, *partes)).encode("utf-8")
    return random.Random(int.from_bytes(hashlib.sha256(texto).digest()[:8], "big"))


def _normal(rng) -> float:
    """Box-Muller usando só random(), estável entre versões do Python."""
    u1, u2 = 1.0 - rng.random(), rng.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _poisson(rng, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam < 30:
        limite, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= rng.random()
            if p <= limite:
                return k
            k += 1
    return max(0, round(lam + math.sqrt(lam) * _normal(rng)))


# ---------------------------------------------------------------------- geração
@dataclass
class BaseSintetica:
    registros: list   # dicts nas COLUNAS_BASE
    surtos: list      # dicts nas COLUNAS_SURTOS
    meta: dict


def _semanas(inicio: date, n: int):
    if inicio.weekday() != 0:
        raise ValueError("O início deve ser uma segunda-feira.")
    return [inicio + timedelta(weeks=i) for i in range(n)]


def _esperado_base(perfil, peso, datas, semente, municipio):
    """λ semanal sem surto: nível x tendência x sazonalidade x ano x município x ruído AR(1)."""
    rng = _rng(semente, perfil.codigo, municipio, "ruido")
    fatores_ano, fatores_mun = {}, {}
    lambdas, ar = [], 0.0
    for i, d in enumerate(datas):
        ano_iso = d.isocalendar()[0]
        if ano_iso not in fatores_ano:
            r = _rng(semente, perfil.codigo, "ano", ano_iso)
            fatores_ano[ano_iso] = math.exp(perfil.sd_ano * _normal(r) - perfil.sd_ano**2 / 2)
            r = _rng(semente, perfil.codigo, municipio, "mun-ano", ano_iso)
            fatores_mun[ano_iso] = math.exp(
                perfil.sd_municipio_ano * _normal(r) - perfil.sd_municipio_ano**2 / 2)
        ar = perfil.rho * ar + perfil.sd_semana * math.sqrt(1 - perfil.rho**2) * _normal(rng)
        sazonal = math.exp(perfil.amplitude_sazonal * math.cos(
            2 * math.pi * (d.timetuple().tm_yday - perfil.pico_dia_ano) / 365.25))
        tendencia = max(0.1, 1 + perfil.tendencia_anual * i / 52)
        lambdas.append(perfil.nivel_aracaju * peso * tendencia * sazonal
                       * fatores_ano[ano_iso] * fatores_mun[ano_iso] * math.exp(ar))
    return lambdas


def _planejar_surtos(perfil, municipio, lambdas, semente):
    """Sorteia 0 a 2 surtos por série, sem sobreposição e com histórico mínimo."""
    rng = _rng(semente, perfil.codigo, municipio, "surtos")
    sorteio = rng.random()
    quantos = 0 if sorteio < 0.35 else (1 if sorteio < 0.85 else 2)
    n, surtos = len(lambdas), []
    for _ in range(quantos):
        for _tentativa in range(20):
            duracao = rng.randint(3, 7)
            if n - duracao - 1 < HISTORICO_MINIMO:
                break
            inicio = rng.randint(HISTORICO_MINIMO, n - duracao - 1)
            fator = round(3.0 + 3.0 * rng.random(), 2)
            livre = all(
                inicio + duracao + INTERVALO_ENTRE_SURTOS <= s["inicio"]
                or s["inicio"] + s["duracao"] + INTERVALO_ENTRE_SURTOS <= inicio
                for s in surtos)
            if livre:
                surtos.append({"inicio": inicio, "duracao": duracao, "fator": fator})
                break
    # perfil triangular: sobe até o meio e desce; sempre > 0 em toda a duração
    for s in surtos:
        d = s["duracao"]
        s["delta"] = []
        for k in range(d):
            peso = 1 - abs(k - (d - 1) / 2) / ((d + 1) / 2)
            base = lambdas[s["inicio"] + k]
            s["delta"].append(max(base * (s["fator"] - 1), PISO_INCREMENTO_PICO) * peso)
    return sorted(surtos, key=lambda s: s["inicio"])


def gerar_base(semente=SEMENTE_PADRAO, inicio=INICIO_PADRAO, semanas=SEMANAS_PADRAO,
               perfis=PERFIS, municipios=MUNICIPIOS) -> BaseSintetica:
    datas = _semanas(inicio, semanas)
    registros, surtos_saida, contador = [], [], 0
    for perfil in perfis:
        for codigo, nome, peso in municipios:
            lambdas = _esperado_base(perfil, peso, datas, semente, codigo)
            planos = _planejar_surtos(perfil, codigo, lambdas, semente)
            adicional = [0.0] * semanas
            for s in planos:
                for k, valor in enumerate(s["delta"]):
                    adicional[s["inicio"] + k] = valor
            rng = _rng(semente, perfil.codigo, codigo, "contagem")
            contagens = [_poisson(rng, lambdas[i] + adicional[i]) for i in range(semanas)]
            for i, d in enumerate(datas):
                ano, sem, _ = d.isocalendar()
                registros.append({
                    "agravo_codigo": perfil.codigo, "agravo_nome": perfil.nome,
                    "municipio_codigo": codigo, "municipio_nome": nome,
                    "ano": ano, "semana_epidemiologica": sem, "contagem": contagens[i]})
            for s in planos:
                contador += 1
                d0 = datas[s["inicio"]]
                ano, sem, _ = d0.isocalendar()
                afetadas = [datas[s["inicio"] + k] for k in range(s["duracao"])]
                surtos_saida.append({
                    "surto_id": f"S{contador:03d}", "agravo_codigo": perfil.codigo,
                    "municipio_codigo": codigo, "ano": ano, "semana_epidemiologica": sem,
                    "semana_inicio": d0.isoformat(), "duracao_semanas": s["duracao"],
                    "fator_pico": s["fator"],
                    "incremento_pico_esperado": round(max(s["delta"]), 2),
                    "incremento_total_esperado": round(sum(s["delta"]), 2),
                    "casos_observados_no_periodo": sum(
                        contagens[s["inicio"]:s["inicio"] + s["duracao"]]),
                    "semanas_afetadas": ";".join(
                        "{}-W{:02d}".format(*x.isocalendar()[:2]) for x in afetadas),
                    "semente": semente})
    meta = {
        "gerador": "ingestao.sintetica.gerador", "versao_gerador": VERSAO_GERADOR,
        "semente": semente, "inicio_segunda": inicio.isoformat(),
        "fim_segunda": datas[-1].isoformat(), "semanas": semanas,
        "municipios": len(municipios), "agravos": len(perfis),
        "registros": len(registros), "surtos_injetados": len(surtos_saida),
        "perfis_agravos": [vars(p) for p in perfis],
        "municipios_pesos": [list(m) for m in municipios],
        "aviso": "Dados fictícios para teste do detector; não representam a epidemiologia real.",
    }
    return BaseSintetica(registros, surtos_saida, meta)


# ------------------------------------------------------------------- serialização
def _csv_texto(colunas, linhas) -> str:
    saida = io.StringIO()
    w = csv.DictWriter(saida, fieldnames=colunas, lineterminator="\n")
    w.writeheader()
    w.writerows(linhas)
    return saida.getvalue()


def serializar(base: BaseSintetica) -> dict:
    """Devolve {sufixo: texto} sem tocar o disco (útil para testar determinismo)."""
    return {
        "base": _csv_texto(COLUNAS_BASE, base.registros),
        "surtos": _csv_texto(COLUNAS_SURTOS, base.surtos),
    }


def sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def catalogos_texto(perfis=PERFIS, municipios=MUNICIPIOS) -> dict:
    mun = _csv_texto(("codigo_ibge", "nome", "uf"),
                     [{"codigo_ibge": c, "nome": n, "uf": "SE"} for c, n, _ in municipios])
    agr = _csv_texto(("codigo", "nome"), [{"codigo": p.codigo, "nome": p.nome} for p in perfis])
    return {"municipios": mun, "agravos": agr}
