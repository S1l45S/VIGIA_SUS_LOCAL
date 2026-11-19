# Dashboard de tendências temporais (PB03 / TF06)

Tela T02: série semanal de notificações com média móvel de 8 semanas e limite
`μ + 2σ`, filtrável por município, agravo e período.

## Como executar

```bash
cp .env.example .env
docker compose up --build            # sobe MongoDB (replica set) e a aplicação
docker compose exec app python manage.py popular_catalogos
docker compose exec app python manage.py importar_dados --arquivo data/datasus/dengue_aracaju.csv
docker compose exec app python manage.py createsuperuser   # usuário de teste local
```

Abra <http://localhost:8000/dashboard/> e entre com o usuário criado. O login é
provisório (admin, exige `is_staff`) até a tela de login do PB06/HU-26 existir;
a rota definitiva é configurada por `DJANGO_LOGIN_URL`.

## Decisões

| Tema | Decisão |
|---|---|
| Fonte dos números | Observado: `RegistroSemanal`. Média e limite: `ResultadoDeteccao`, calculados na carga (ADR-004). A view não calcula estatística. |
| Seleção inicial (RF002) | Município com mais notificações; dentro dele, o agravo com mais notificações. |
| Período padrão | Últimas 52 semanas da série, terminando na semana mais recente carregada. |
| "sem notificações no período" | Exibida quando não há linhas **ou** todas as semanas valem zero, em vez de gráfico vazio (US01). |
| Histórico insuficiente | Semanas sem 8 anteriores consecutivas não têm banda; o painel avisa (RN04). |
| Rótulo da semana | SE real calculada de `semana_inicio` (segunda) menos 1 dia, via `calendario.semana_da_data`. O par ano/semana gravado é ISO e pode diferir da SE em alguns anos. |
| Gráfico offline | Chart.js 4.4.7 servido localmente (`static/dashboard/vendor`), sem CDN (HU-19). |
| Segurança | `login_required` + somente GET; dados do banco escapados pelo template; JSON via `json_script`. |

## Testes

```bash
docker compose --profile test run --rm tests
# só o dashboard, mostrando os tempos de RNF001:
pytest --ds=config.settings dashboard -q -s
```

`test_desempenho.py` cria 10.000 registros (20 municípios × 5 agravos × 100
semanas), faz 30 requisições e exige p95 < 3 s. Mede o **servidor** (consulta +
HTML). Para o tempo total percebido, abra o DevTools (aba Network/Performance)
e confira que o gráfico aparece em menos de 3 s; registre o valor no relatório.

## Compatibilidade verificada

| Cenário | Versões | Resultado |
|---|---|---|
| Imagem principal / CI (`Dockerfile`, `requirements.txt`) | Python 3.14.10, Django 6.1.3, django-mongodb-backend 6.1.0, pymongo 4.19.0, pandas 3.1.1, numpy 2.5.4 | 149 testes passando, `ruff` e `manage.py check` limpos |
| Imagem de ingestão (`Dockerfile.ingestao`) | mesmo conjunto, com pandas 2.3.3 | 149 testes passando |

O app `dashboard` não importa pandas nem pysus; o `pysus==2.11.7` só é usado
pela imagem de ingestão e não foi instalado nesta verificação (exige GDAL).
MongoDB usado: 8.3 em replica set (o `compose.yaml` usa 7.0).

## Limitações conhecidas

- Login provisório via admin (depende do PB06).
- Seleção de período por datas (campos `date`), não por lista de anos como no
  protótipo T01.
- Não há exportação nem ajuste de limiar na interface (fora do escopo, RN02).
