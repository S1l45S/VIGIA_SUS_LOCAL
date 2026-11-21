"""Backtest do detector sobre a base sintética rotulada (HU-16, OBJ02, R02/R10).

Não usa banco: chama ``processar_series(..., persistir=False)``, isto é, o mesmo
cálculo (μ+2σ, 8 semanas) que gera os resultados reais. Mede as DUAS definições de
falso positivo do plano (DP04) e a detecção por surto.
"""

from collections import defaultdict
from datetime import date

from deteccao.services.estatistica import processar_series

META_DETECCAO = 1.0           # OBJ02: 100% dos surtos simulados
META_FALSOS_POSITIVOS = 0.15  # OBJ02: abaixo de 15%
FAIXAS = (("média < 1", 0, 1), ("1 ≤ média < 5", 1, 5), ("média ≥ 5", 5, float("inf")))


def _semana_inicio(linha):
    return date.fromisocalendar(int(linha["ano"]), int(linha["semana_epidemiologica"]), 1)


def _chave(surto, semana):
    return (surto["agravo_codigo"], surto["municipio_codigo"], semana)


def _taxa(a, b):
    return a / b if b else 0.0


def _pct(x):
    return f"{100 * x:.1f}%"


def _semanas_de_surto(surtos):
    afetadas, por_surto = set(), {}
    for s in surtos:
        semanas = []
        for rotulo in s["semanas_afetadas"].split(";"):
            ano, sem = rotulo.split("-W")
            semanas.append(date.fromisocalendar(int(ano), int(sem), 1))
        por_surto[s["surto_id"]] = (s, semanas)
        afetadas.update(_chave(s, d) for d in semanas)
    return afetadas, por_surto


def _bloco(alertas, falsos, normais):
    return {
        "alertas": alertas,
        "falsos_positivos": falsos,
        "semanas_normais": normais,
        "fp_sobre_alertas": _taxa(falsos, alertas),             # definição A (precisão)
        "fp_sobre_semanas_normais": _taxa(falsos, normais),     # definição B (por semana)
    }


def executar_backtest(registros, surtos, janela=8):
    detector = [
        {
            "agravo_codigo": r["agravo_codigo"],
            "municipio_codigo": r["municipio_codigo"],
            "semana_inicio": _semana_inicio(r),
            "quantidade": int(r["contagem"]),
        }
        for r in registros
    ]
    resultados = processar_series(detector, janela=janela, persistir=False)
    afetadas, por_surto = _semanas_de_surto(surtos)

    def chave_r(r):
        return (r["agravo_codigo"], r["municipio_codigo"], r["semana_inicio"])

    anomalias = {chave_r(r) for r in resultados if r["anomalia"]}

    # --- detecção por surto
    detalhe, det_qualquer, det_precoce = [], 0, 0
    for sid, (s, semanas) in por_surto.items():
        qualquer = any(_chave(s, d) in anomalias for d in semanas)
        precoce = any(_chave(s, d) in anomalias for d in semanas[:2])
        det_qualquer += qualquer
        det_precoce += precoce
        detalhe.append({
            "surto_id": sid,
            "agravo_codigo": s["agravo_codigo"],
            "municipio_codigo": s["municipio_codigo"],
            "detectado": qualquer,
            "detectado_nas_2_primeiras": precoce,
        })

    # --- falsos positivos: semana sinalizada fora de qualquer surto injetado
    def calcular(filtro):
        sel = [r for r in resultados if filtro(r)]
        normais = sum(1 for r in sel if chave_r(r) not in afetadas)
        alertas = [r for r in sel if r["anomalia"]]
        falsos = sum(1 for r in alertas if chave_r(r) not in afetadas)
        return _bloco(len(alertas), falsos, normais)

    por_agravo = {
        a: calcular(lambda r, a=a: r["agravo_codigo"] == a)
        for a in sorted({r["agravo_codigo"] for r in resultados})
    }
    por_faixa = {
        nome: calcular(lambda r, lo=lo, hi=hi: lo <= r["media_movel"] < hi)
        for nome, lo, hi in FAIXAS
    }
    geral = calcular(lambda r: True)

    det_por_agravo = defaultdict(lambda: [0, 0])
    for d in detalhe:
        det_por_agravo[d["agravo_codigo"]][0] += 1
        det_por_agravo[d["agravo_codigo"]][1] += d["detectado"]

    n = len(por_surto)
    return {
        "janela": janela,
        "semanas_avaliadas": len(resultados),
        "alertas": geral["alertas"],
        "surtos": n,
        "deteccao_qualquer_semana": _taxa(det_qualquer, n),
        "deteccao_nas_2_primeiras_semanas": _taxa(det_precoce, n),
        "surtos_nao_detectados": [d for d in detalhe if not d["detectado"]],
        "geral": geral,
        "por_agravo": por_agravo,
        "por_faixa": por_faixa,
        "deteccao_por_agravo": {
            a: {"surtos": v[0], "detectados": v[1]} for a, v in sorted(det_por_agravo.items())
        },
        "atende_obj02": (
            n > 0
            and _taxa(det_qualquer, n) >= META_DETECCAO
            and geral["fp_sobre_alertas"] < META_FALSOS_POSITIVOS
        ),
    }


def relatorio_markdown(m, meta, nomes_agravos):
    g = m["geral"]
    detectados = m["surtos"] - len(m["surtos_nao_detectados"])
    ok_det = "atende" if m["deteccao_qualquer_semana"] >= META_DETECCAO else "NÃO atende"
    ok_fp = "atende" if g["fp_sobre_alertas"] < META_FALSOS_POSITIVOS else "NÃO atende"
    linhas = [
        f"# Backtest do detector — base sintética (semente {meta['semente']})",
        "",
        (
            f"Detector: média móvel de {m['janela']} semanas, limite μ+2σ (RN02). "
            f"Base: {meta['registros']} registros, {meta['municipios']} municípios, "
            f"{meta['agravos']} agravos, {meta['semanas']} semanas, {m['surtos']} surtos "
            "injetados. Dados fictícios: o resultado mostra o comportamento do código, não "
            "o desempenho epidemiológico real (R20)."
        ),
        "",
        "## Resultado geral (OBJ02)",
        "",
        "| Métrica | Valor | Meta | Situação |",
        "|---|---|---|---|",
        (
            f"| Surtos detectados (qualquer semana do surto) | "
            f"{_pct(m['deteccao_qualquer_semana'])} ({detectados}/{m['surtos']}) | 100% | {ok_det} |"
        ),
        (
            f"| Surtos detectados nas 2 primeiras semanas | "
            f"{_pct(m['deteccao_nas_2_primeiras_semanas'])} | — | informativo |"
        ),
        (
            f"| Falsos positivos / alertas (def. A) | {_pct(g['fp_sobre_alertas'])} "
            f"({g['falsos_positivos']}/{g['alertas']}) | < 15% | {ok_fp} |"
        ),
        (
            f"| Falsos positivos / semanas normais (def. B) | "
            f"{_pct(g['fp_sobre_semanas_normais'])} "
            f"({g['falsos_positivos']}/{g['semanas_normais']}) | — | informativo |"
        ),
        "",
        "## Por agravo",
        "",
        "| Agravo | Surtos detectados | Alertas | Falsos pos. | FP/alertas (A) | FP/sem. normais (B) |",
        "|---|---|---|---|---|---|",
    ]
    for cod, b in m["por_agravo"].items():
        d = m["deteccao_por_agravo"].get(cod, {"surtos": 0, "detectados": 0})
        linhas.append(
            f"| {nomes_agravos.get(cod, cod)} | {d['detectados']}/{d['surtos']} | "
            f"{b['alertas']} | {b['falsos_positivos']} | {_pct(b['fp_sobre_alertas'])} | "
            f"{_pct(b['fp_sobre_semanas_normais'])} |"
        )
    linhas += [
        "",
        "## Por faixa de contagem (média das 8 semanas anteriores)",
        "",
        "| Faixa | Alertas | Falsos pos. | FP/alertas (A) | FP/sem. normais (B) |",
        "|---|---|---|---|---|",
    ]
    for nome, b in m["por_faixa"].items():
        linhas.append(
            f"| {nome} | {b['alertas']} | {b['falsos_positivos']} | "
            f"{_pct(b['fp_sobre_alertas'])} | {_pct(b['fp_sobre_semanas_normais'])} |"
        )
    if m["surtos_nao_detectados"]:
        linhas += ["", "## Surtos não detectados", ""]
        linhas += [
            f"- {d['surto_id']} ({nomes_agravos.get(d['agravo_codigo'])}, "
            f"município {d['municipio_codigo']})"
            for d in m["surtos_nao_detectados"]
        ]
    return "\n".join(linhas) + "\n"
