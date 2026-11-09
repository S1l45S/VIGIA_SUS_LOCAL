# Modelo de dados — VigiaSUS Local

**Status:** proposta inicial para PB01  
**Persistência:** MongoDB  
**Escopo:** estrutura de dados da aplicação e ingestão de arquivos agregados  
**Última revisão:** 08/11/2026

## 1. Objetivo

Este documento registra as decisões iniciais de modelagem do VigiaSUS Local, as coleções previstas, os relacionamentos lógicos, os índices necessários e os pontos que ainda dependem de validação durante a implementação de PB01.

A modelagem deve permitir armazenar séries temporais agregadas por município, agravo e período epidemiológico, mantendo rastreabilidade da origem dos dados e das cargas realizadas.

## 2. Princípios de modelagem

1. **Dados agregados:** a aplicação deve armazenar contagens agregadas, não registros identificáveis de pacientes.
2. **Rastreabilidade:** cada registro importado deve poder ser relacionado à carga que o originou.
3. **Idempotência:** reprocessar o mesmo arquivo não deve criar duplicações silenciosas.
4. **Integridade:** combinações que representem o mesmo município, agravo e período devem ser únicas, conforme a granularidade aprovada.
5. **Validação na aplicação:** os dados devem ser validados antes da persistência. Não se deve depender exclusivamente da estrutura flexível do MongoDB.
6. **Evolução controlada:** mudanças no contrato de dados e na estrutura das coleções devem ser documentadas.

## 3. Coleções propostas

Os nomes abaixo são nomes lógicos. A implementação deverá confirmar os nomes físicos usados pelo backend Django/MongoDB.

### 3.1 `municipios`

Cadastro de municípios utilizados nas análises.

| Campo | Tipo lógico | Obrigatório | Regra |
|---|---|---:|---|
| `codigo_ibge` | string | Sim | Código IBGE; armazenar como texto para preservar formato |
| `nome` | string | Sim | Nome oficial do município |
| `uf` | string | Sim | Sigla da unidade federativa |
| `ativo` | boolean | Sim | Indica se o município está disponível para uso |

**Chave natural:** `codigo_ibge`.

### 3.2 `agravos`

Catálogo de agravos disponíveis para ingestão e análise.

| Campo | Tipo lógico | Obrigatório | Regra |
|---|---|---:|---|
| `codigo` | string | Sim | Código estável definido pela fonte ou pelo catálogo do projeto |
| `nome` | string | Sim | Denominação do agravo |
| `ativo` | boolean | Sim | Indica se o agravo está disponível |

**Chave natural:** `codigo`.

> A definição do código deve respeitar a codificação da fonte de dados adotada. Não criar códigos substitutos sem documentar o mapeamento.

### 3.3 `cargas_dados`

Registra cada tentativa de importação.

| Campo | Tipo lógico | Obrigatório | Regra |
|---|---|---:|---|
| `origem` | string | Sim | Identificação da fonte ou sistema de origem |
| `arquivo_nome` | string | Sim | Nome do arquivo recebido |
| `arquivo_hash` | string | Recomendado | Hash do conteúdo para detectar reenvio do mesmo arquivo |
| `iniciada_em` | datetime | Sim | Data/hora de início |
| `finalizada_em` | datetime | Não | Data/hora de término |
| `status` | string | Sim | `EM_ANDAMENTO`, `CONCLUIDA`, `CONCLUIDA_COM_REJEICOES` ou `FALHA` |
| `total_linhas` | integer | Sim | Quantidade de linhas de dados lidas |
| `total_importados` | integer | Sim | Quantidade de registros persistidos |
| `total_rejeitados` | integer | Sim | Quantidade de linhas rejeitadas |
| `mensagem_erro` | string | Não | Resumo técnico, sem dados pessoais ou segredos |

A carga deve ser criada e atualizada de modo que uma falha não deixe o processo registrado incorretamente como concluído.

### 3.4 `rejeicoes_ingestao`

Registra problemas encontrados em linhas do arquivo.

| Campo | Tipo lógico | Obrigatório | Regra |
|---|---|---:|---|
| `carga_id` | referência lógica | Sim | Identificador da carga |
| `numero_linha` | integer | Sim | Número da linha no arquivo, incluindo cabeçalho na contagem |
| `codigo_erro` | string | Sim | Código estável do tipo de rejeição |
| `mensagem` | string | Sim | Descrição objetiva da rejeição |
| `valores_relevantes` | object | Não | Apenas campos não sensíveis necessários para diagnóstico |

Não copiar a linha inteira para a coleção de rejeições sem antes aplicar a política de minimização de dados.

### 3.5 `registros_semanais`

Armazena a série temporal agregada.

| Campo | Tipo lógico | Obrigatório | Regra |
|---|---|---:|---|
| `agravo_codigo` | string | Sim | Código do agravo |
| `municipio_codigo` | string | Sim | Código IBGE do município |
| `ano` | integer | Sim | Ano de referência |
| `semana_epidemiologica` | integer | Sim | Semana conforme calendário epidemiológico adotado |
| `semana_inicio` | date | Condicional | Data inicial, se definida pela fonte/calendário |
| `quantidade` | integer | Sim | Contagem não negativa |
| `carga_id` | referência lógica | Sim | Carga responsável pela inclusão/atualização |
| `fonte_registro` | string | Sim | Identificação da fonte |

**Chave natural proposta:** `agravo_codigo + municipio_codigo + ano + semana_epidemiologica`.

A chave deve ser revista se a fonte possuir outra dimensão relevante, como sexo, faixa etária, classificação, unidade notificadora ou situação do caso. Não descartar dimensões presentes no arquivo oficial.

## 4. Relacionamentos lógicos

- Um município pode estar associado a muitos registros semanais.
- Um agravo pode estar associado a muitos registros semanais.
- Uma carga pode gerar muitos registros semanais.
- Uma carga pode gerar muitas rejeições.
- Cada registro semanal referencia um município, um agravo e uma carga.

No MongoDB, esses vínculos podem ser implementados por referências escalares (códigos/identificadores) em vez de documentos embutidos. A escolha evita duplicar os catálogos em cada observação e facilita a rastreabilidade.

## 5. Índices propostos

| Coleção | Índice | Tipo | Finalidade |
|---|---|---|---|
| `municipios` | `codigo_ibge` | Único | Impedir municípios duplicados |
| `agravos` | `codigo` | Único | Impedir agravos duplicados |
| `cargas_dados` | `arquivo_hash` | Não único ou único conforme política | Detectar reenvio de arquivo |
| `cargas_dados` | `status`, `iniciada_em` | Composto | Consultar histórico de cargas |
| `rejeicoes_ingestao` | `carga_id`, `numero_linha` | Único | Evitar duplicação da rejeição da mesma linha na mesma carga |
| `registros_semanais` | `agravo_codigo`, `municipio_codigo`, `ano`, `semana_epidemiologica` | Único composto | Garantir granularidade única |
| `registros_semanais` | `municipio_codigo`, `agravo_codigo`, `ano`, `semana_epidemiologica` | Composto | Consultas de séries por município e agravo |

A ordem dos campos de índices compostos deve ser validada com as consultas reais. Evitar criar índices redundantes sem evidência de necessidade.

## 6. Regras de integridade

- `codigo_ibge`, códigos de agravo e códigos de origem devem ser tratados como texto.
- `quantidade` deve ser inteiro e maior ou igual a zero.
- Ano e semana epidemiológica devem pertencer ao calendário aceito pela fonte.
- Município e agravo devem existir nos respectivos catálogos ou ser tratados segundo uma política explícita de cadastro.
- Duplicidades dentro do mesmo arquivo devem ser detectadas antes da gravação.
- A política para duplicidade deve ser explícita: rejeitar, substituir ou agregar. A implementação inicial deve rejeitar ambiguidades, salvo decisão formal diferente.
- A importação deve registrar totais lidos, importados e rejeitados.
- Não armazenar CPF, CNS, nome, endereço, data de nascimento ou outros identificadores pessoais no conjunto de dados agregados.

## 7. Transações e consistência

A consistência da carga deve ser testada no ambiente MongoDB utilizado pelo projeto. Operações transacionais do MongoDB dependem de implantação compatível com transações, como replica set ou cluster fragmentado.

Antes de assumir atomicidade como garantida, executar uma prova de conceito que:
1. grave um conjunto de registros;
2. provoque uma falha controlada no meio da operação;
3. confirme se as gravações foram revertidas;
4. confirme que o estado da carga e as rejeições permanecem coerentes.

Se a implantação ou o backend não oferecer a garantia necessária, documentar a estratégia alternativa de lote, compensação e reprocessamento. Não afirmar atomicidade sem teste automatizado.

## 8. Decisões pendentes

| Item | Situação | Como fechar |
|---|---|---|
| Backend de integração Django/MongoDB | Confirmar na implementação | Escolher e padronizar uma única integração; não misturar APIs de backends diferentes |
| Granularidade final da série | Pendente de contrato oficial | Conferir todas as dimensões do CSV/fonte |
| Calendário epidemiológico | Pendente | Adotar regra oficial da fonte; não presumir que semana ISO é equivalente |
| Política de duplicidade | Proposta: rejeitar ambiguidades | Registrar decisão e testar |
| Atomicidade da carga | Pendente de PoC | Testar no mesmo tipo de cluster usado no projeto |
| Cadastro automático de municípios/agravos | Pendente | Definir se catálogo será pré-carregado ou validado durante a ingestão |

## 9. Limitações conhecidas

- Esta modelagem é uma proposta de PB01 e não substitui o contrato oficial da fonte de dados.
- A estrutura final depende da inspeção de arquivos reais e da confirmação de suas dimensões.
- O suporte a recursos específicos do Django ORM varia conforme o backend MongoDB escolhido; índices, restrições e migrações devem ser validados por testes.
- A importação de arquivo local não equivale à integração definitiva com uma pasta compartilhada ou fonte externa.
- A ingestão histórica do DATASUS deve ser documentada também quanto à fonte, período, recorte geográfico, atualização e transformação, sem misturar dados de fontes distintas.

## 10. Testes mínimos

- Criação e consulta dos catálogos.
- Rejeição de códigos de município e agravo inválidos.
- Rejeição de quantidade negativa ou não inteira.
- Unicidade da chave natural de `registros_semanais`.
- Detecção de duplicidade dentro do mesmo arquivo.
- Rastreabilidade entre registro, carga e rejeição.
- Reprocessamento do mesmo arquivo e verificação de idempotência.
- Falha controlada durante a gravação e verificação de consistência.
- Verificação de criação e uso dos índices.
