# Base sintética rotulada (P1 D02, P2 BaseSinteticaRotulada)

Dados **fictícios** de dengue, zika, chikungunya, leishmaniose e sífilis congênita para 20 municípios de
Sergipe, 100 semanas (ISO 2024-W42 a 2026-W37), semente 42: 10.000 registros e 71 surtos injetados.
Níveis, sazonalidade e pesos dos municípios são ilustrativos; não usar como evidência epidemiológica (R20).

| Arquivo | Conteúdo |
|---|---|
| `base_sintetica_s42.csv` | Contrato da ingestão (`agravo_codigo, agravo_nome, municipio_codigo, municipio_nome, ano, semana_epidemiologica, contagem`) |
| `surtos_injetados_s42.csv` | Verdade-terreno: semana de início, duração, fator de pico, incremento esperado e semanas afetadas |
| `base_sintetica_s42.meta.json` | Semente, parâmetros, perfis, pesos e SHA-256 dos arquivos |
| `catalogo_municipios.csv`, `catalogo_agravos.csv` | Catálogos para `popular_catalogos` |
| `relatorio_backtest_s42.md` | Detecção e falsos positivos do detector (μ+2σ, 8 semanas) |

## Uso
```bash
python manage.py popular_catalogos --municipios data/sinteticos/catalogo_municipios.csv \
                                   --agravos data/sinteticos/catalogo_agravos.csv
python manage.py importar_dados --arquivo data/sinteticos/base_sintetica_s42.csv
python manage.py gerar_alertas            # se o PB04 estiver instalado
python manage.py backtest_sintetico       # recalcula o relatório (sem banco)
python manage.py gerar_base_sintetica --semente 7 --semanas 120   # outra base
```
Mesma semente + mesmos parâmetros = arquivos idênticos byte a byte (RNF005).
Códigos dos agravos: CID-10 de base (A90, A92.8, A92.0, B55, A50); ajuste no catálogo se a fonte oficial usar outro.
