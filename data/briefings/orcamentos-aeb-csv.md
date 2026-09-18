# Estrutura do dataset: orcamentos-aeb-csv

## Resumo

Dados de **execução orçamentária federal** (Orçamento da União) de **2000 a 2019**,
restritos a **dois órgãos**:

- **Agência Espacial Brasileira (AEB)**
- **Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC)**

Não há dados de outros ministérios, órgãos, estados ou municípios neste dataset. Perguntas
sobre orçamento de outras áreas de governo (saúde, educação, segurança etc.) **não podem ser
respondidas** com este dataset.

Granularidade: cada linha representa o valor orçamentário de uma **ação orçamentária**,
dentro de um **programa**, de uma **unidade orçamentária**, em um **ano** específico
(não há granularidade mensal/diária, nem por credor/fornecedor, nem por empenho individual).

## Estrutura de diretórios e arquivos

```
dados_gerais/
└── tb_geral.csv              # tabela única, já "achatada" (join completo)
dados_normalizados/
├── tb_orcamentos.csv         # tabela fato (valores + chaves estrangeiras)
├── tb_acoes.csv              # dimensão: ações orçamentárias
├── tb_programas.csv          # dimensão: programas orçamentários
├── tb_unidades_orcamentarias.csv  # dimensão: unidades orçamentárias (órgãos)
└── tb_anos.csv               # dimensão: anos
metadados/
└── metadados.csv             # descrição textual dos campos de tb_geral (separador ";")
```

**Importante:** `dados_gerais/tb_geral.csv` é o **join completo** das tabelas de
`dados_normalizados/` — cada linha de `tb_geral.csv` corresponde exatamente a uma linha de
`tb_orcamentos.csv` com os nomes já resolvidos a partir das tabelas de dimensão. São a
**mesma informação em dois formatos**, não dados complementares.

- Para perguntas simples (filtrar/somar/agrupar por unidade, programa, ação ou ano), use
  `tb_geral.csv` diretamente — é mais simples porque já tem tudo em uma tabela só.
- Para perguntas sobre a relação entre entidades (ex.: "quantos programas uma ação já
  passou?", "quantas ações um programa tem?"), pode ser mais direto usar as tabelas de
  `dados_normalizados/`.

Todos os arquivos CSV usam vírgula (`,`) como separador de campo e aspas duplas (`"`) para
delimitar valores, exceto `metadados/metadados.csv`, que usa ponto e vírgula (`;`) e não é
propriamente um dado, apenas um dicionário de dados textual.

## Dicionário de campos

### `dados_gerais/tb_geral.csv` (tabela achatada)

| Campo            | Tipo           | Significado                                                                 | Sinônimos / termos equivalentes |
|------------------|----------------|------------------------------------------------------------------------------|----------------------------------|
| `id_orcamento`   | inteiro (PK)   | Identificador único do registro orçamentário (uma combinação ano+unidade+programa+ação) | id, chave, identificador |
| `data_ano`       | inteiro (ano)  | Ano/exercício orçamentário a que o registro se refere                        | ano, exercício, exercício financeiro, ano fiscal, ano orçamentário |
| `nome_unidade`   | texto          | Nome da unidade orçamentária (órgão) responsável                             | órgão, ministério, agência, unidade gestora, UO |
| `nome_programa`  | texto          | Nome do programa orçamentário ao qual a ação pertence                        | programa de governo, programa orçamentário |
| `nome_acao`      | texto          | Nome da ação orçamentária específica                                         | ação orçamentária, atividade, projeto, iniciativa |
| `dotacao_atual`  | numérico (R$)  | Valor da dotação orçamentária atual (autorizado) para a ação no ano          | dotação, orçamento previsto, valor autorizado, crédito orçamentário, LOA+créditos |
| `empenhado`      | numérico (R$)  | Valor empenhado (reservado/comprometido) para a ação no ano                  | empenho, valor comprometido, gasto empenhado |
| `liquidado`      | numérico (R$)  | Valor liquidado (bem/serviço já entregue/verificado) para a ação no ano      | liquidação, valor liquidado |
| `pago`           | numérico (R$)  | Valor efetivamente pago para a ação no ano                                   | pagamento, valor pago, desembolso, gasto executado, execução financeira |

Todos os valores monetários estão em **reais (R$)**, em valores nominais (não há campo de
valor corrigido/deflacionado). Não há indicação de que os valores estejam em milhares — os
números aparentam ser o valor cheio em reais (ex.: `42750` = R$ 42.750,00).

> Observação sobre `metadados/metadados.csv`: as descrições ali contidas (ex.: "Valor
> disponível para a realização da ação" para `empenhado`, "Valor homologado para a ação"
> para `pago`) usam redação própria da fonte e não correspondem literalmente à terminologia
> oficial do ciclo orçamentário brasileiro. A tabela acima usa a terminologia padrão
> (dotação → empenho → liquidação → pagamento), que é a mais utilizada em perguntas sobre
> orçamento público.

### `dados_normalizados/tb_orcamentos.csv` (tabela fato)

| Campo           | Tipo         | Significado                                              |
|-----------------|--------------|-----------------------------------------------------------|
| `id_orcamento`  | inteiro (PK) | Mesmo identificador de `tb_geral.csv`                     |
| `dotacao_atual` | numérico     | Igual a `tb_geral.dotacao_atual`                          |
| `empenhado`     | numérico     | Igual a `tb_geral.empenhado`                              |
| `liquidado`     | numérico     | Igual a `tb_geral.liquidado`                              |
| `pago`          | numérico     | Igual a `tb_geral.pago`                                   |
| `fk_acao`       | inteiro (FK) | Referencia `tb_acoes.id_acao`                             |
| `fk_programa`   | inteiro (FK) | Referencia `tb_programas.id_programa`                     |
| `fk_unidade`    | inteiro (FK) | Referencia `tb_unidades_orcamentarias.id_unidade`         |
| `fk_ano`        | inteiro (FK) | Referencia `tb_anos.id_ano`                                |

### Tabelas de dimensão

- `tb_acoes.csv`: `id_acao` (PK), `nome_acao` — 116 ações distintas, todas com nomes únicos.
- `tb_programas.csv`: `id_programa` (PK), `nome_programa` — 13 programas distintos.
- `tb_unidades_orcamentarias.csv`: `id_unidade` (PK), `nome_unidade` — apenas 2 registros
  (AEB e MCTIC).
- `tb_anos.csv`: `id_ano` (PK), `data_ano` — 20 registros, anos de 2000 a 2019.

## Relacionamentos entre as tabelas

```
tb_orcamentos (fato)
 ├── fk_acao      → tb_acoes.id_acao
 ├── fk_programa  → tb_programas.id_programa
 ├── fk_unidade   → tb_unidades_orcamentarias.id_unidade
 └── fk_ano       → tb_anos.id_ano
```

- Todas as chaves estrangeiras em `tb_orcamentos.csv` são válidas (não há FK órfã).
- `tb_geral.csv` = `tb_orcamentos` já unida (`JOIN`) com as quatro tabelas de dimensão,
  substituindo os IDs pelos nomes correspondentes.
- **Uma mesma ação pode estar associada a mais de um programa** ao longo dos anos (34 das
  116 ações aparecem sob mais de um programa em anos diferentes — reflexo de
  reorganizações do Plano Plurianual/classificação orçamentária ao longo do tempo). Ou
  seja, a relação ação↔programa **não é fixa**: para saber a qual programa uma ação
  pertenceu em determinado ano, é preciso olhar o registro daquele ano específico, não
  assumir uma relação 1:1 permanente entre ação e programa.
- Cada unidade orçamentária está associada a vários programas (AEB: 11 programas; MCTIC: 7
  programas), com alguma sobreposição possível entre unidades (ex.: programas
  administrativos/de gestão que existem em ambas).

## Cobertura e limitações (o que o dataset consegue e não consegue responder)

**Consegue responder:**
- Qual foi a dotação/empenho/liquidação/pagamento de uma unidade, programa ou ação em um
  ano ou intervalo de anos (2000–2019).
- Comparações de execução orçamentária (ex.: pago vs. empenhado, taxa de execução) por
  ano, unidade, programa ou ação.
- Evolução histórica (série temporal 2000–2019) de valores orçamentários para AEB e MCTIC.
- Rankings: quais ações/programas tiveram maior dotação, maior valor pago, etc., dentro do
  escopo AEB/MCTIC.
- Quantidade de ações/programas distintos por unidade ou por ano.

**Não consegue responder:**
- Qualquer pergunta sobre órgãos/ministérios diferentes de AEB e MCTIC.
- Dados de 2020 em diante, ou anteriores a 2000.
- Execução orçamentária em granularidade mensal, por empenho individual, por
  fornecedor/credor, por fonte de recurso, por natureza de despesa (pessoal, custeio,
  investimento) — o dataset não possui esses campos.
- Valores corrigidos pela inflação (todos os valores são nominais, do ano correspondente).
- Motivos/justificativas de variação orçamentária (não há campos textuais explicativos além
  dos nomes de programa/ação).

## Qualidade dos dados / observações relevantes para consultas

- 438 registros no total, sem valores nulos, sem `id_orcamento` duplicado.
- Nenhum valor monetário negativo.
- Em 36 registros, `pago = 0` (ação com dotação/empenho mas sem pagamento realizado no
  ano — comum em obras/projetos plurianuais).
- Em 8 registros, `empenhado` é maior que `dotacao_atual` (provavelmente reflexo de
  créditos suplementares/remanejamentos não totalmente refletidos no campo de dotação
  informado). Ao comparar dotação com execução, considerar que pequenas inconsistências
  desse tipo existem nos dados originais.
- Nem sempre vale `dotacao_atual ≥ empenhado ≥ liquidado ≥ pago` (ver ponto acima); a
  relação `liquidado ≥ pago` e `empenhado ≥ liquidado`, por outro lado, se mantém na
  amostra observada.
