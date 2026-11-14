# Contrato de CSV — VigiaSUS Local

**Status:** proposta inicial; confirmar com amostras oficiais antes de estabilizar  
**Responsável técnico:** equipe do projeto  
**Última revisão:** 12/11/2026

## 1. Objetivo e escopo

Definir o formato de entrada, as regras de validação e o comportamento esperado do processo de ingestão de dados agregados no VigiaSUS Local.

Este contrato descreve um formato interno normalizado para PB01. Ele não afirma que esse seja o layout nativo de exportação do DATASUS. Arquivos oficiais devem ser inspecionados e transformados para este formato por um adaptador específico, preservando a rastreabilidade da fonte.

## 2. Formato proposto

- Formato: CSV (texto delimitado).
- Codificação recomendada: UTF-8.
- Delimitador: vírgula (`,`) no contrato normalizado.
- Cabeçalho: obrigatório, na primeira linha.
- Aspas: conforme convenção CSV; campos com delimitador, aspas ou quebra de linha devem ser corretamente escapados.
- Decimal: não aplicável aos campos de contagem.
- Linhas em branco: rejeitar ou ignorar com registro explícito; a implementação deve adotar uma única política.
- Arquivo: extensão `.csv`.

Se os arquivos de origem utilizarem ponto e vírgula, Latin-1 ou outra convenção, o adaptador de origem deverá normalizar o conteúdo sem alterar os valores.

## 3. Cabeçalho proposto

```csv
agravo_codigo,agravo_nome,municipio_codigo,municipio_nome,ano,semana_epidemiologica,contagem
```

| Coluna | Tipo | Obrigatória | Regra |
|---|---|---:|---|
| `agravo_codigo` | texto | Sim | Código reconhecido no catálogo/mapeamento |
| `agravo_nome` | texto | Sim | Nome do agravo; deve corresponder ao código ou ao mapeamento |
| `municipio_codigo` | texto | Sim | Código IBGE válido |
| `municipio_nome` | texto | Sim | Nome compatível com o código do município |
| `ano` | inteiro | Sim | Ano válido dentro do período aceito |
| `semana_epidemiologica` | inteiro | Sim | Semana válida segundo o calendário definido para a fonte |
| `contagem` | inteiro | Sim | Contagem maior ou igual a zero |

**Semana no CSV gerado pela ingestão do SINAN.** O gerador traduz cada semana
epidemiológica (domingo a sábado) para a semana ISO da segunda-feira seguinte, porque a
validação da carga lê `ano` e `semana_epidemiologica` como semana ISO. Essa regra
fica registrada no campo `calendario_do_csv` do arquivo `.meta.json`.

### Exemplo ilustrativo

```csv
agravo_codigo,agravo_nome,municipio_codigo,municipio_nome,ano,semana_epidemiologica,contagem
AGR001,Agravo demonstrativo,2800308,Aracaju,2025,1,12
AGR001,Agravo demonstrativo,2800308,Aracaju,2025,2,15
```

Os códigos e valores acima são apenas ilustrativos. Não representam dados oficiais nem devem ser usados como carga de produção.

## 4. Regras de validação

### 4.1 Arquivo

- O arquivo deve existir e ser legível.
- A extensão e o conteúdo devem corresponder a CSV.
- O arquivo deve possuir cabeçalho.
- O cabeçalho deve conter todas as colunas obrigatórias, sem nomes duplicados.
- Colunas inesperadas devem ser tratadas conforme política explícita: rejeitar o arquivo ou aceitar apenas após atualização documentada do contrato.
- Arquivo vazio ou sem linhas de dados deve resultar em mensagem clara e status definido.

### 4.2 Linha

- Não aceitar campos obrigatórios vazios.
- Remover espaços periféricos de campos textuais antes da validação.
- Validar códigos contra catálogos ou tabelas de correspondência.
- Validar coerência entre código e nome do município/agravo.
- `ano`, `semana_epidemiologica` e `contagem` devem ser inteiros.
- `contagem` não pode ser negativa.
- Semana epidemiológica deve ser válida para o ano e para o calendário da fonte.
- Não aceitar identificadores pessoais ou colunas com dados pessoais.
- A linha rejeitada deve ser identificada pelo número da linha e por código/mensagem de erro.

### 4.3 Duplicidade

A chave de negócio proposta para identificar uma observação é:

`agravo_codigo + municipio_codigo + ano + semana_epidemiologica`

Se houver mais de uma linha com a mesma chave no mesmo arquivo, o comportamento inicial recomendado é rejeitar as linhas conflitantes ou o arquivo, conforme política aprovada. Não somar valores automaticamente sem confirmação de que as linhas representam parcelas aditivas.

Se a mesma chave já existir no banco, a estratégia de reprocessamento deve ser explícita e testada: ignorar idempotentemente, substituir por versão mais recente ou rejeitar conflito. A escolha deve considerar a origem e a data de atualização.

## 5. Privacidade e minimização

O contrato é destinado a dados agregados. Não incluir nem persistir, entre outros:

- nome de paciente;
- CPF;
- CNS/cartão SUS;
- endereço;
- telefone;
- data de nascimento;
- identificadores individuais ou combinações que permitam identificar pessoas.

Se a fonte fornecer dados individualizados, eles não devem ser importados por este contrato. É necessário definir processo separado, base legal, controles de acesso e avaliação de privacidade antes de qualquer tratamento.

## 6. Comportamento da ingestão

O comando Django previsto é:

```powershell
python manage.py importar_dados --arquivo "caminho/arquivo.csv"
```

O comando deve:

1. validar os argumentos;
2. registrar uma tentativa de carga;
3. ler o arquivo de forma segura;
4. validar cabeçalho e linhas;
5. contabilizar linhas lidas, aceitas e rejeitadas;
6. persistir dados válidos segundo a política transacional aprovada;
7. persistir rejeições com número da linha e motivo;
8. finalizar a carga com status coerente;
9. exibir resumo da execução e código de saída apropriado.

A política para arquivos parcialmente válidos deve ser configurada e documentada. A proposta inicial é permitir identificar rejeições por linha, mas não declarar a carga concluída integralmente quando houver rejeições.

## 7. Códigos de erro sugeridos

| Código | Significado |
|---|---|
| `CSV_FILE_NOT_FOUND` | Arquivo não encontrado |
| `CSV_ENCODING_INVALID` | Codificação não suportada ou inválida |
| `CSV_HEADER_MISSING` | Cabeçalho ausente |
| `CSV_HEADER_INVALID` | Colunas obrigatórias ausentes ou duplicadas |
| `CSV_EMPTY_ROW` | Linha vazia |
| `REQUIRED_FIELD_EMPTY` | Campo obrigatório vazio |
| `INVALID_INTEGER` | Valor inteiro inválido |
| `INVALID_QUANTITY` | Contagem negativa ou fora do domínio |
| `UNKNOWN_MUNICIPALITY` | Município não reconhecido |
| `UNKNOWN_AGRAVO` | Agravo não reconhecido |
| `INCONSISTENT_NAME_CODE` | Nome não corresponde ao código |
| `INVALID_EPI_WEEK` | Semana epidemiológica inválida |
| `DUPLICATE_IN_FILE` | Chave duplicada no mesmo arquivo |
| `DUPLICATE_IN_DATABASE` | Conflito com registro existente |
| `PERSONAL_DATA_COLUMN` | Coluna incompatível com o contrato agregado |

Os códigos são uma proposta para padronizar logs, testes e relatórios. A implementação pode ampliá-los mantendo compatibilidade.

## 8. Testes obrigatórios

| Cenário | Resultado esperado |
|---|---|
| CSV válido | Registros persistidos e carga concluída |
| Arquivo inexistente | Erro claro; nenhuma observação gravada |
| Arquivo vazio | Carga não concluída, com motivo registrado |
| Cabeçalho ausente | Arquivo rejeitado |
| Coluna obrigatória ausente | Arquivo rejeitado |
| Campo obrigatório vazio | Linha rejeitada |
| Quantidade não inteira | Linha rejeitada |
| Quantidade negativa | Linha rejeitada |
| Município desconhecido | Linha rejeitada |
| Agravo desconhecido | Linha rejeitada |
| Semana fora do calendário | Linha rejeitada |
| Chave duplicada no arquivo | Aplicação da política de duplicidade |
| Mesmo arquivo reprocessado | Resultado idempotente conforme política |
| Falha durante persistência | Estado consistente, sem sucesso falso |
| Coluna com dado pessoal | Arquivo/linha bloqueado conforme política |

## 9. Dados históricos e fontes oficiais

Para ingestão de dados históricos do DATASUS:

- registrar a fonte oficial específica e a tabela/sistema de origem;
- preservar o arquivo bruto original em local controlado, quando permitido;
- documentar período de referência, data de extração e recorte geográfico;
- mapear o layout oficial para o CSV normalizado;
- registrar transformações, filtros e códigos de correspondência;
- validar o calendário epidemiológico usado pela fonte;
- não presumir que todos os agravos compartilham o mesmo layout ou nível de agregação.

A solicitação de série histórica de pelo menos cinco anos para Aracaju deve ser tratada como escopo específico de ingestão histórica e ter seus critérios de extração e validação registrados separadamente do contrato genérico de PB01.

## 10. Limitações conhecidas e decisões pendentes

| Item | Situação |
|---|---|
| Layout oficial de cada arquivo DATASUS | Ainda requer inspeção de amostras reais |
| Separador e codificação dos arquivos de origem | Podem variar; adaptador deve normalizar |
| Calendário epidemiológico | O gerador do SINAN faz a tradução explícita para a semana ISO equivalente e a registra no `.meta.json`; confirmar com a equipe se esse é o critério definitivo |
| Dimensões adicionais (sexo, faixa etária, classificação etc.) | Verificar nos arquivos antes de fechar a chave de negócio |
| Política de carga parcial | Aprovar entre rejeição integral e importação parcial controlada |
| Política de reprocessamento | Aprovar e cobrir com testes |
| Integração com pasta compartilhada | Não é comprovada pelo comando que lê caminho local |
| Atualização automática/agendada | Fora do escopo deste contrato inicial, salvo decisão posterior |

## 11. Critério para estabilizar o contrato

O contrato só deve ser marcado como estável quando:

1. uma ou mais amostras reais da fonte forem inspecionadas;
2. todas as dimensões relevantes estiverem mapeadas;
3. o calendário epidemiológico estiver definido;
4. a política de duplicidade e reprocessamento estiver aprovada;
5. os testes obrigatórios estiverem automatizados;
6. a documentação e os exemplos forem atualizados com dados sintéticos ou anonimizados.

## 12. Ingestão do SINAN (dengue, Aracaju)

O arquivo `data/datasus/dengue_aracaju.csv` é gerado pelo comando `baixar_sinan`, que
baixa os arquivos do SINAN pelo PySUS, conta as notificações por município e semana,
completa as semanas sem caso com zero e grava o CSV neste contrato. O comando não grava
no banco. A carga é feita depois, por `importar_dados`.

Ao lado de cada CSV é gravado um `.meta.json` com:

- fonte, agravo e período (`AAAASS`);
- nome e hash `sha256` de cada arquivo bruto e do próprio CSV;
- linhas lidas, notificações contadas e descartes por motivo;
- data da extração e o calendário usado nas semanas.

Por padrão as quatro últimas semanas da fonte são cortadas (`--cortar-ultimas`), porque as
semanas mais recentes costumam ter notificações ainda incompletas.

A conta de conferência é: linhas lidas, menos os descartes da fonte, menos os descartes da
agregação, igual às notificações contadas.
