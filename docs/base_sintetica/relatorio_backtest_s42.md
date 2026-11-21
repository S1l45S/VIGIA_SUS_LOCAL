# Backtest do detector — base sintética (semente 42)

Detector: média móvel de 8 semanas, limite μ+2σ (RN02). Base: 10000 registros, 20 municípios, 5 agravos, 100 semanas, 71 surtos injetados. Dados fictícios: o resultado mostra o comportamento do código, não o desempenho epidemiológico real (R20).

## Resultado geral (OBJ02)

| Métrica | Valor | Meta | Situação |
|---|---|---|---|
| Surtos detectados (qualquer semana do surto) | 97.2% (69/71) | 100% | NÃO atende |
| Surtos detectados nas 2 primeiras semanas | 88.7% | — | informativo |
| Falsos positivos / alertas (def. A) | 82.3% (682/829) | < 15% | NÃO atende |
| Falsos positivos / semanas normais (def. B) | 7.7% (682/8842) | — | informativo |

## Por agravo

| Agravo | Surtos detectados | Alertas | Falsos pos. | FP/alertas (A) | FP/sem. normais (B) |
|---|---|---|---|---|---|
| Sífilis congênita | 12/12 | 169 | 144 | 85.2% | 8.1% |
| Dengue | 16/17 | 156 | 123 | 78.8% | 7.0% |
| Chikungunya | 15/16 | 183 | 154 | 84.2% | 8.7% |
| Zika | 14/14 | 183 | 153 | 83.6% | 8.6% |
| Leishmaniose | 12/12 | 138 | 108 | 78.3% | 6.1% |

## Por faixa de contagem (média das 8 semanas anteriores)

| Faixa | Alertas | Falsos pos. | FP/alertas (A) | FP/sem. normais (B) |
|---|---|---|---|---|
| média < 1 | 625 | 525 | 84.0% | 8.4% |
| 1 ≤ média < 5 | 161 | 128 | 79.5% | 6.2% |
| média ≥ 5 | 43 | 29 | 67.4% | 5.9% |

## Surtos não detectados

- S006 (Dengue, município 2807402)
- S034 (Chikungunya, município 2803500)
